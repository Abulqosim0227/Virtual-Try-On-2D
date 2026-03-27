import numpy as np
import torch
from PIL import Image
from torchvision import transforms

from vto.api.exceptions import ModelLoadError, PreprocessingError
from vto.config import settings
from vto.pipeline.context import TryOnContext
from vto.pipeline.preprocessors.base import BasePreprocessor

SCHP_LABELS = {
    0: "background", 1: "hat", 2: "hair", 3: "sunglasses",
    4: "upper_clothes", 5: "skirt", 6: "pants", 7: "dress",
    8: "belt", 9: "left_shoe", 10: "right_shoe", 11: "head",
    12: "left_leg", 13: "right_leg", 14: "left_arm", 15: "right_arm",
    16: "bag", 17: "scarf",
}


class SCHPPreprocessor(BasePreprocessor):
    def __init__(self) -> None:
        self._model = None
        self._transform = transforms.Compose([
            transforms.Resize((512, 512)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.406, 0.456, 0.485], std=[0.225, 0.224, 0.229]),
        ])

    @property
    def name(self) -> str:
        return "schp"

    def load(self) -> None:
        weights_path = settings.weights_dir / "schp"
        if not weights_path.exists():
            raise ModelLoadError(f"SCHP weights not found at {weights_path}")

        try:
            checkpoint = _find_checkpoint(weights_path)
            self._model = torch.load(checkpoint, map_location=settings.device)
            if hasattr(self._model, "eval"):
                self._model.eval()
            if hasattr(self._model, "half"):
                self._model.half()
        except Exception as e:
            raise ModelLoadError(f"Failed to load SCHP: {e}")

    def unload(self) -> None:
        if self._model is not None:
            del self._model
            self._model = None
            torch.cuda.empty_cache()

    def process(self, context: TryOnContext) -> TryOnContext:
        if self._model is None:
            raise PreprocessingError("SCHP not loaded")

        try:
            input_tensor = self._transform(context.person_image).unsqueeze(0)
            input_tensor = input_tensor.to(settings.device, dtype=torch.float16)

            with torch.no_grad():
                output = self._model(input_tensor)

            if isinstance(output, (list, tuple)):
                output = output[0]

            parsed = output.argmax(dim=1).squeeze(0).cpu().numpy().astype(np.uint8)

            parsed_resized = np.array(
                Image.fromarray(parsed).resize(
                    context.person_image.size, Image.NEAREST
                )
            )
            context.parsed_mask = parsed_resized
        except Exception as e:
            raise PreprocessingError(f"SCHP failed: {e}")

        return context

    def vram_estimate_mb(self) -> int:
        return 1500


def _find_checkpoint(weights_dir) -> str:
    for ext in ("*.pth", "*.pt", "*.ckpt"):
        files = list(weights_dir.glob(ext))
        if files:
            return str(files[0])
    raise ModelLoadError(f"No checkpoint found in {weights_dir}")
