"""SCHP human parsing. Source: github.com/Zheng-Chong/CatVTON (CC BY-NC-SA 4.0)."""

from vto.pipeline.models.catvton_lib.schp import networks
from vto.pipeline.models.catvton_lib.schp.utils.transforms import get_affine_transform, transform_logits

from collections import OrderedDict
import torch
import numpy as np
import cv2
from PIL import Image
from torchvision import transforms

dataset_settings = {
    'lip': {
        'input_size': [473, 473],
        'num_classes': 20,
        'label': ['Background', 'Hat', 'Hair', 'Glove', 'Sunglasses', 'Upper-clothes', 'Dress', 'Coat',
                  'Socks', 'Pants', 'Jumpsuits', 'Scarf', 'Skirt', 'Face', 'Left-arm', 'Right-arm',
                  'Left-leg', 'Right-leg', 'Left-shoe', 'Right-shoe']
    },
    'atr': {
        'input_size': [512, 512],
        'num_classes': 18,
        'label': ['Background', 'Hat', 'Hair', 'Sunglasses', 'Upper-clothes', 'Skirt', 'Pants', 'Dress', 'Belt',
                  'Left-shoe', 'Right-shoe', 'Face', 'Left-leg', 'Right-leg', 'Left-arm', 'Right-arm', 'Bag', 'Scarf']
    },
}


class SCHP:
    def __init__(self, ckpt_path, device):
        dataset_type = None
        if 'lip' in ckpt_path:
            dataset_type = 'lip'
        elif 'atr' in ckpt_path:
            dataset_type = 'atr'
        assert dataset_type is not None, 'Dataset type not found in checkpoint path'
        self.device = device
        self.num_classes = dataset_settings[dataset_type]['num_classes']
        self.input_size = dataset_settings[dataset_type]['input_size']
        self.aspect_ratio = self.input_size[1] * 1.0 / self.input_size[0]

        self.label = dataset_settings[dataset_type]['label']
        self.model = networks.init_model('resnet101', num_classes=self.num_classes, pretrained=None).to(device)
        self._load_ckpt(ckpt_path)
        self.model.eval()

        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.406, 0.456, 0.485], std=[0.225, 0.224, 0.229])
        ])
        self.upsample = torch.nn.Upsample(size=self.input_size, mode='bilinear', align_corners=True)

    def _load_ckpt(self, ckpt_path):
        rename_map = {
            "decoder.conv3.2.weight": "decoder.conv3.3.weight",
            "decoder.conv3.3.weight": "decoder.conv3.4.weight",
            "decoder.conv3.3.bias": "decoder.conv3.4.bias",
            "decoder.conv3.3.running_mean": "decoder.conv3.4.running_mean",
            "decoder.conv3.3.running_var": "decoder.conv3.4.running_var",
            "fushion.3.weight": "fushion.4.weight",
            "fushion.3.bias": "fushion.4.bias",
        }
        state_dict = torch.load(ckpt_path, map_location='cpu')['state_dict']
        new_state_dict = OrderedDict()
        for k, v in state_dict.items():
            new_state_dict[k[7:]] = v  # remove `module.`
        renamed = OrderedDict()
        for k, v in new_state_dict.items():
            renamed[rename_map.get(k, k)] = v
        self.model.load_state_dict(renamed, strict=False)

    def _box2cs(self, box):
        x, y, w, h = box[:4]
        center = np.array([x + w * 0.5, y + h * 0.5], dtype=np.float32)
        if w > self.aspect_ratio * h:
            h = w * 1.0 / self.aspect_ratio
        elif w < self.aspect_ratio * h:
            w = h * self.aspect_ratio
        return center, np.array([w, h], dtype=np.float32)

    @torch.no_grad()
    def __call__(self, image):
        if isinstance(image, str):
            img = cv2.imread(image, cv2.IMREAD_COLOR)
        elif isinstance(image, Image.Image):
            img = np.array(image)
        else:
            img = image

        h, w = img.shape[:2]
        center, s = self._box2cs([0, 0, w - 1, h - 1])
        trans = get_affine_transform(center, s, 0, self.input_size)
        inp = cv2.warpAffine(
            img, trans, (self.input_size[1], self.input_size[0]),
            flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0)
        )
        inp = self.transform(inp).to(self.device).unsqueeze(0)

        output = self.model(inp)
        upsample_output = self.upsample(output).permute(0, 2, 3, 1)[0]
        logits = transform_logits(upsample_output.cpu().numpy(), center, s, w, h, self.input_size)
        parsing = np.argmax(logits, axis=2).astype(np.uint8)
        return Image.fromarray(parsing)
