import structlog
import torch
from PIL import Image

from vto.api.exceptions import ModelLoadError, VRAMExhaustedError
from vto.config import settings
from vto.pipeline.context import TryOnContext
from vto.pipeline.models.base import BaseVTOModel

logger = structlog.get_logger()

BASE_MODEL = "booksforcharlie/stable-diffusion-inpainting"
ATTN_CKPT_VERSION = "mix"
HEIGHT = 1024
WIDTH = 768

TIER_PARAMS = {
    "fast": {"num_inference_steps": 50, "guidance_scale": 2.5, "blur_factor": 9},
    "hd": {"num_inference_steps": 100, "guidance_scale": 3.5, "blur_factor": 9},
}


class CatVTONModel(BaseVTOModel):
    def __init__(self) -> None:
        self._pipeline = None
        self._masker = None

    @property
    def name(self) -> str:
        return "catvton"

    def load(self) -> None:
        weights_path = settings.weights_dir / "catvton"
        if not weights_path.exists():
            raise ModelLoadError(f"CatVTON weights not found at {weights_path}")

        try:
            from vto.pipeline.models.catvton_lib import CatVTONPipeline
            from vto.pipeline.models.catvton_lib.masker import AutoMasker

            self._pipeline = CatVTONPipeline(
                base_ckpt=BASE_MODEL,
                attn_ckpt=str(weights_path),
                attn_ckpt_version=ATTN_CKPT_VERSION,
                weight_dtype=torch.bfloat16,
                device=settings.device,
                compile=True,
                skip_safety_check=True,
                use_tf32=True,
            )

            densepose_path = str(settings.weights_dir / "densepose" / "densepose_r50_fpn_dl.torchscript")
            schp_dir = str(weights_path / "SCHP")
            self._masker = AutoMasker(
                densepose_path=densepose_path,
                schp_ckpt_dir=schp_dir,
                device=settings.device,
            )
            logger.info("masker_loaded", type="densepose+schp")

        except torch.cuda.OutOfMemoryError:
            raise VRAMExhaustedError("Not enough VRAM to load CatVTON")
        except Exception as e:
            raise ModelLoadError(f"Failed to load CatVTON: {e}")

    def unload(self) -> None:
        if self._pipeline is not None:
            del self._pipeline
            self._pipeline = None
        if self._masker is not None:
            del self._masker
            self._masker = None
        import gc
        gc.collect()
        torch.cuda.empty_cache()

    def generate(self, context: TryOnContext) -> Image.Image:
        if self._pipeline is None:
            raise ModelLoadError("CatVTON not loaded")

        try:
            params = TIER_PARAMS.get(context.tier, TIER_PARAMS["fast"])

            mask = self._get_mask(context, params["blur_factor"])

            results = self._pipeline(
                image=context.person_image,
                condition_image=context.garment_image,
                mask=mask,
                num_inference_steps=params["num_inference_steps"],
                guidance_scale=params["guidance_scale"],
                height=HEIGHT,
                width=WIDTH,
                generator=torch.Generator(device=settings.device).manual_seed(42),
            )
            return results[0]

        except torch.cuda.OutOfMemoryError:
            raise VRAMExhaustedError("OOM during CatVTON inference")
        except Exception as e:
            raise ModelLoadError(f"CatVTON inference failed: {e}")

    def vram_estimate_mb(self) -> int:
        return 4000

    def _get_mask(self, context: TryOnContext, blur_factor: int) -> Image.Image:
        if self._masker is not None:
            category_map = {"upper": "upper", "lower": "lower", "full": "overall"}
            cloth_type = category_map.get(context.category, "upper")
            return self._masker(context.person_image, cloth_type, blur_factor=blur_factor)

        return Image.new("L", context.person_image.size, 255)
