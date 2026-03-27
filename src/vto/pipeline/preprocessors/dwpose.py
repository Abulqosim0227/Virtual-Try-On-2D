import numpy as np
import torch

from vto.api.exceptions import ModelLoadError, PreprocessingError
from vto.config import settings
from vto.pipeline.context import TryOnContext
from vto.pipeline.preprocessors.base import BasePreprocessor


class DWPosePreprocessor(BasePreprocessor):
    def __init__(self) -> None:
        self._model = None

    @property
    def name(self) -> str:
        return "dwpose"

    def load(self) -> None:
        weights_path = settings.weights_dir / "dwpose"
        if not weights_path.exists():
            raise ModelLoadError(f"DWPose weights not found at {weights_path}")

        try:
            from controlnet_aux import DWposeDetector

            self._model = DWposeDetector.from_pretrained(
                str(weights_path),
                torch_dtype=torch.float16,
            ).to(settings.device)
        except ImportError:
            raise ModelLoadError("Install controlnet_aux: pip install controlnet-aux")
        except Exception as e:
            raise ModelLoadError(f"Failed to load DWPose: {e}")

    def unload(self) -> None:
        if self._model is not None:
            del self._model
            self._model = None
            torch.cuda.empty_cache()

    def process(self, context: TryOnContext) -> TryOnContext:
        if self._model is None:
            raise PreprocessingError("DWPose not loaded")

        try:
            pose_image = self._model(
                context.person_image,
                output_type="np",
                detect_resolution=context.person_image.height,
                image_resolution=context.person_image.height,
            )
            context.pose_keypoints = np.array(pose_image)
        except Exception as e:
            raise PreprocessingError(f"DWPose failed: {e}")

        return context

    def vram_estimate_mb(self) -> int:
        return 1500
