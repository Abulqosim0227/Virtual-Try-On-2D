"""
Automatic mask generator for CatVTON.
Uses DensePose (TorchScript, no detectron2) + dual SCHP (ATR + LIP).
Matches CatVTON's production AutoMasker logic.
"""

import os

import cv2
import numpy as np
import torch
from diffusers.image_processor import VaeImageProcessor
from PIL import Image
from torch.nn import functional as F

from vto.pipeline.models.catvton_lib.schp import SCHP

DENSE_INDEX_MAP = {
    "background": [0],
    "torso": [1, 2],
    "right hand": [3],
    "left hand": [4],
    "right foot": [5],
    "left foot": [6],
    "right thigh": [7, 9],
    "left thigh": [8, 10],
    "right leg": [11, 13],
    "left leg": [12, 14],
    "left big arm": [15, 17],
    "right big arm": [16, 18],
    "left forearm": [19, 21],
    "right forearm": [20, 22],
    "face": [23, 24],
    "thighs": [7, 8, 9, 10],
    "legs": [11, 12, 13, 14],
    "hands": [3, 4],
    "feet": [5, 6],
    "big arms": [15, 16, 17, 18],
    "forearms": [19, 20, 21, 22],
}

ATR_MAPPING = {
    'Background': 0, 'Hat': 1, 'Hair': 2, 'Sunglasses': 3,
    'Upper-clothes': 4, 'Skirt': 5, 'Pants': 6, 'Dress': 7,
    'Belt': 8, 'Left-shoe': 9, 'Right-shoe': 10, 'Face': 11,
    'Left-leg': 12, 'Right-leg': 13, 'Left-arm': 14, 'Right-arm': 15,
    'Bag': 16, 'Scarf': 17
}

LIP_MAPPING = {
    'Background': 0, 'Hat': 1, 'Hair': 2, 'Glove': 3,
    'Sunglasses': 4, 'Upper-clothes': 5, 'Dress': 6, 'Coat': 7,
    'Socks': 8, 'Pants': 9, 'Jumpsuits': 10, 'Scarf': 11,
    'Skirt': 12, 'Face': 13, 'Left-arm': 14, 'Right-arm': 15,
    'Left-leg': 16, 'Right-leg': 17, 'Left-shoe': 18, 'Right-shoe': 19
}

PROTECT_BODY_PARTS = {
    'upper': ['Left-leg', 'Right-leg'],
    'lower': ['Right-arm', 'Left-arm', 'Face'],
    'overall': [],
}

PROTECT_CLOTH_PARTS = {
    'upper': {'ATR': ['Skirt', 'Pants'], 'LIP': ['Skirt', 'Pants']},
    'lower': {'ATR': ['Upper-clothes'], 'LIP': ['Upper-clothes', 'Coat']},
    'overall': {'ATR': [], 'LIP': []},
}

MASK_CLOTH_PARTS = {
    'upper': ['Upper-clothes', 'Coat', 'Dress', 'Jumpsuits'],
    'lower': ['Pants', 'Skirt', 'Dress', 'Jumpsuits'],
    'overall': ['Upper-clothes', 'Dress', 'Pants', 'Skirt', 'Coat', 'Jumpsuits'],
}

MASK_DENSE_PARTS = {
    'upper': ['torso', 'big arms', 'forearms'],
    'lower': ['thighs', 'legs'],
    'overall': ['torso', 'thighs', 'legs', 'big arms', 'forearms'],
}


class AutoMasker:
    def __init__(self, densepose_path: str, schp_ckpt_dir: str, device: str = 'cuda'):
        import torchvision  # noqa: F401 — registers torchvision ops for TorchScript

        self.device = device
        self._densepose = torch.jit.load(densepose_path).eval().to(device).float()

        atr_path = os.path.join(schp_ckpt_dir, 'exp-schp-201908301523-atr.pth')
        lip_path = os.path.join(schp_ckpt_dir, 'exp-schp-201908261155-lip.pth')
        self.schp_atr = SCHP(ckpt_path=atr_path, device=device)
        self.schp_lip = SCHP(ckpt_path=lip_path, device=device)

        self.mask_processor = VaeImageProcessor(
            vae_scale_factor=8, do_normalize=False, do_binarize=True, do_convert_grayscale=True
        )

    @torch.no_grad()
    def __call__(self, person_image: Image.Image, cloth_type: str = 'upper',
                 blur_factor: int = 5) -> Image.Image:
        densepose_map = self._run_densepose(person_image)
        atr_parse = np.array(self.schp_atr(person_image))
        lip_parse = np.array(self.schp_lip(person_image))

        mask = _build_mask(densepose_map, lip_parse, atr_parse, cloth_type)
        mask = self.mask_processor.blur(Image.fromarray(mask), blur_factor=blur_factor)
        return mask

    def _run_densepose(self, image: Image.Image) -> np.ndarray:
        img_arr = np.array(image)
        h, w = img_arr.shape[:2]

        max_size = 1024
        scale = min(max_size / max(h, w), 1.0)
        if scale < 1.0:
            img_resized = cv2.resize(img_arr, (int(w * scale), int(h * scale)))
        else:
            img_resized = img_arr

        tensor = torch.from_numpy(img_resized).to(self.device)
        outputs = self._densepose(tensor)

        pred_boxes = outputs[0]
        coarse_segm = outputs[1]
        fine_segm = outputs[2]

        rh, rw = img_resized.shape[:2]
        result = np.zeros((rh, rw), dtype=np.uint8)

        if pred_boxes.shape[0] > 0:
            box = pred_boxes[0].cpu()
            x1, y1, x2, y2 = box.int().tolist()
            bw, bh = max(x2 - x1, 1), max(y2 - y1, 1)

            coarse = coarse_segm[0].unsqueeze(0)
            fine = fine_segm[0].unsqueeze(0)

            coarse_bbox = F.interpolate(coarse, (bh, bw), mode="bilinear", align_corners=False).argmax(dim=1)
            fg_mask = (coarse_bbox > 0).long()
            labels = F.interpolate(fine, (bh, bw), mode="bilinear", align_corners=False).argmax(dim=1) * fg_mask
            labels = labels.squeeze(0).cpu().numpy().astype(np.uint8)

            y1c, x1c = max(y1, 0), max(x1, 0)
            y2c, x2c = min(y1 + bh, rh), min(x1 + bw, rw)
            ly1, lx1 = y1c - y1, x1c - x1
            ly2, lx2 = ly1 + (y2c - y1c), lx1 + (x2c - x1c)
            result[y1c:y2c, x1c:x2c] = labels[ly1:ly2, lx1:lx2]

        if scale < 1.0:
            result = cv2.resize(result, (w, h), interpolation=cv2.INTER_NEAREST)

        return result


def _build_mask(densepose: np.ndarray, lip_parse: np.ndarray, atr_parse: np.ndarray,
                cloth_type: str) -> np.ndarray:
    w, h = densepose.shape[1], densepose.shape[0]

    dilate_size = max(w, h) // 250
    dilate_size = dilate_size if dilate_size % 2 == 1 else dilate_size + 1
    dilate_kernel = np.ones((dilate_size, dilate_size), np.uint8)

    blur_size = max(w, h) // 25
    blur_size = blur_size if blur_size % 2 == 1 else blur_size + 1

    # Strong protect: hands + feet (DensePose) intersected with SCHP arm/leg labels + face
    hands_protect = _dense_mask(['hands', 'feet'], densepose)
    hands_protect = cv2.dilate(hands_protect.astype(np.uint8), dilate_kernel, iterations=1)
    arm_leg_schp = (
        _part_mask(['Left-arm', 'Right-arm', 'Left-leg', 'Right-leg'], atr_parse, ATR_MAPPING) |
        _part_mask(['Left-arm', 'Right-arm', 'Left-leg', 'Right-leg'], lip_parse, LIP_MAPPING)
    )
    hands_protect = hands_protect & arm_leg_schp.astype(np.uint8)
    face_protect = _part_mask(['Face'], lip_parse, LIP_MAPPING)
    strong_protect = hands_protect.astype(bool) | face_protect

    # Weak protect: hair, irrelevant body parts, irrelevant clothes, accessories
    body_protect = (
        _part_mask(PROTECT_BODY_PARTS[cloth_type], lip_parse, LIP_MAPPING) |
        _part_mask(PROTECT_BODY_PARTS[cloth_type], atr_parse, ATR_MAPPING)
    )
    hair_protect = (
        _part_mask(['Hair'], lip_parse, LIP_MAPPING) |
        _part_mask(['Hair'], atr_parse, ATR_MAPPING)
    )
    cloth_protect = (
        _part_mask(PROTECT_CLOTH_PARTS[cloth_type]['LIP'], lip_parse, LIP_MAPPING) |
        _part_mask(PROTECT_CLOTH_PARTS[cloth_type]['ATR'], atr_parse, ATR_MAPPING)
    )
    accessory_parts = ['Hat', 'Glove', 'Sunglasses', 'Bag', 'Left-shoe', 'Right-shoe', 'Scarf', 'Socks']
    accessory_protect = (
        _part_mask(accessory_parts, lip_parse, LIP_MAPPING) |
        _part_mask(accessory_parts, atr_parse, ATR_MAPPING)
    )
    weak_protect = body_protect | cloth_protect | hair_protect | strong_protect | accessory_protect

    # Mask area: clothing labels (SCHP) + body surface (DensePose)
    strong_mask = (
        _part_mask(MASK_CLOTH_PARTS[cloth_type], lip_parse, LIP_MAPPING) |
        _part_mask(MASK_CLOTH_PARTS[cloth_type], atr_parse, ATR_MAPPING)
    )
    background = (
        _part_mask(['Background'], lip_parse, LIP_MAPPING) &
        _part_mask(['Background'], atr_parse, ATR_MAPPING)
    )

    # DensePose body region mask — this is the key addition over SCHP-only
    dense_mask = _dense_mask(MASK_DENSE_PARTS[cloth_type], densepose)
    orig_shape = dense_mask.shape[:2]
    dense_small = cv2.resize(dense_mask.astype(np.uint8), None, fx=0.25, fy=0.25,
                             interpolation=cv2.INTER_NEAREST)
    dense_small = cv2.dilate(dense_small, dilate_kernel, iterations=2)
    dense_mask = cv2.resize(dense_small, (orig_shape[1], orig_shape[0]),
                            interpolation=cv2.INTER_NEAREST)

    # Combine: not-protected & not-background, plus DensePose regions
    mask = (np.ones_like(densepose) & (~weak_protect) & (~background)) | dense_mask.astype(bool)

    # Convex hull
    mask_255 = (mask * 255).astype(np.uint8)
    contours, _ = cv2.findContours(mask_255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    hull_img = np.zeros_like(mask_255)
    if contours:
        all_pts = np.concatenate(contours)
        hull = cv2.convexHull(all_pts)
        cv2.fillPoly(hull_img, [hull], 255)
    mask = (hull_img // 255) & (~weak_protect).astype(np.uint8)

    # Gaussian blur to smooth
    mask_blurred = cv2.GaussianBlur((mask * 255).astype(np.uint8), (blur_size, blur_size), 0)
    mask_blurred[mask_blurred < 25] = 0
    mask_blurred[mask_blurred >= 25] = 1

    # Force clothing, exclude strong protect, dilate
    mask_final = (mask_blurred | strong_mask.astype(np.uint8)) & (~strong_protect).astype(np.uint8)
    mask_final = cv2.dilate(mask_final.astype(np.uint8), dilate_kernel, iterations=1)

    return (mask_final * 255).astype(np.uint8)


def _part_mask(parts: list, parse: np.ndarray, mapping: dict) -> np.ndarray:
    mask = np.zeros_like(parse, dtype=bool)
    for part in parts:
        if part not in mapping:
            continue
        idx = mapping[part]
        if isinstance(idx, list):
            for i in idx:
                mask = mask | (parse == i)
        else:
            mask = mask | (parse == idx)
    return mask


def _dense_mask(parts: list, densepose: np.ndarray) -> np.ndarray:
    mask = np.zeros_like(densepose, dtype=bool)
    for part in parts:
        if part not in DENSE_INDEX_MAP:
            continue
        for idx in DENSE_INDEX_MAP[part]:
            mask = mask | (densepose == idx)
    return mask
