import torch
from PIL import Image

from vto.api.exceptions import ModelLoadError, VRAMExhaustedError
from vto.config import settings
from vto.pipeline.context import TryOnContext
from vto.pipeline.models.base import BaseVTOModel

NUM_INFERENCE_STEPS = 100
GUIDANCE_SCALE = 2.0


class IDMVTONModel(BaseVTOModel):
    def __init__(self) -> None:
        self._pipeline = None

    @property
    def name(self) -> str:
        return "idm_vton"

    def load(self) -> None:
        weights_path = settings.weights_dir / "idm_vton"
        if not weights_path.exists():
            raise ModelLoadError(f"IDM-VTON weights not found at {weights_path}")

        try:
            self._pipeline = _load_idm_pipeline(weights_path)
        except ImportError:
            raise ModelLoadError(
                "Install dependencies: pip install diffusers transformers accelerate"
            )
        except torch.cuda.OutOfMemoryError:
            raise VRAMExhaustedError("Not enough VRAM to load IDM-VTON")
        except Exception as e:
            raise ModelLoadError(f"Failed to load IDM-VTON: {e}")

    def unload(self) -> None:
        if self._pipeline is not None:
            del self._pipeline
            self._pipeline = None
            import gc
            gc.collect()
            torch.cuda.empty_cache()

    def generate(self, context: TryOnContext) -> Image.Image:
        if self._pipeline is None:
            raise ModelLoadError("IDM-VTON not loaded")

        try:
            result = self._pipeline(
                image=context.person_image,
                garment=context.garment_image,
                garment_mask=context.garment_mask,
                pose_image=_keypoints_to_image(context),
                mask_image=_build_clothing_mask(context),
                num_inference_steps=NUM_INFERENCE_STEPS,
                guidance_scale=GUIDANCE_SCALE,
                generator=torch.Generator(device="cpu").manual_seed(42),
            )

            if hasattr(result, "images"):
                return result.images[0]
            return result

        except torch.cuda.OutOfMemoryError:
            raise VRAMExhaustedError("OOM during IDM-VTON inference")
        except Exception as e:
            raise ModelLoadError(f"IDM-VTON inference failed: {e}")

    def vram_estimate_mb(self) -> int:
        return 12000


def _load_idm_pipeline(weights_path):
    from diffusers import StableDiffusionInpaintPipeline

    pipe = StableDiffusionInpaintPipeline.from_pretrained(
        str(weights_path),
        torch_dtype=torch.float16,
        safety_checker=None,
    )

    pipe.enable_model_cpu_offload()
    pipe.set_progress_bar_config(disable=True)

    return pipe


def _keypoints_to_image(context: TryOnContext) -> Image.Image:
    if context.pose_keypoints is not None:
        return Image.fromarray(context.pose_keypoints.astype("uint8"))
    return Image.new("RGB", context.person_image.size, (0, 0, 0))


def _build_clothing_mask(context: TryOnContext) -> Image.Image:
    if context.parsed_mask is not None:
        import numpy as np

        mask = context.parsed_mask.copy()
        clothing_labels = {4, 5, 6, 7}
        binary = np.isin(mask, list(clothing_labels)).astype("uint8") * 255
        return Image.fromarray(binary).convert("L")

    return Image.new("L", context.person_image.size, 255)
