import torch
from PIL import Image

from vto.api.exceptions import ModelLoadError, PreprocessingError
from vto.config import settings
from vto.pipeline.context import TryOnContext
from vto.pipeline.preprocessors.base import BasePreprocessor


class RMBGPreprocessor(BasePreprocessor):
    def __init__(self) -> None:
        self._pipeline = None

    @property
    def name(self) -> str:
        return "rmbg"

    def load(self) -> None:
        weights_path = settings.weights_dir / "rmbg"
        if not weights_path.exists():
            raise ModelLoadError(f"RMBG weights not found at {weights_path}")

        try:
            from transformers import pipeline

            self._pipeline = pipeline(
                "image-segmentation",
                model=str(weights_path),
                torch_dtype=torch.float16,
                device=settings.device,
                trust_remote_code=True,
            )
        except ImportError:
            raise ModelLoadError("Install transformers: pip install transformers")
        except Exception as e:
            raise ModelLoadError(f"Failed to load RMBG: {e}")

    def unload(self) -> None:
        if self._pipeline is not None:
            del self._pipeline
            self._pipeline = None
            torch.cuda.empty_cache()

    def process(self, context: TryOnContext) -> TryOnContext:
        if self._pipeline is None:
            raise PreprocessingError("RMBG not loaded")

        try:
            results = self._pipeline(context.garment_image)

            mask = _extract_mask(results, context.garment_image.size)
            context.garment_mask = Image.composite(
                context.garment_image,
                Image.new("RGB", context.garment_image.size, (255, 255, 255)),
                mask,
            )
        except Exception as e:
            raise PreprocessingError(f"RMBG failed: {e}")

        return context

    def vram_estimate_mb(self) -> int:
        return 1000


def _extract_mask(results: list[dict], target_size: tuple[int, int]) -> Image.Image:
    for item in results:
        if "mask" in item:
            mask = item["mask"]
            if mask.size != target_size:
                mask = mask.resize(target_size, Image.BILINEAR)
            return mask.convert("L")

    raise PreprocessingError("RMBG returned no mask")
