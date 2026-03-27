from PIL import Image, ImageFilter

from vto.pipeline.context import TryOnContext
from vto.pipeline.models.base import BaseVTOModel


class MockVTOModel(BaseVTOModel):
    @property
    def name(self) -> str:
        return "mock"

    def load(self) -> None:
        pass

    def unload(self) -> None:
        pass

    def generate(self, context: TryOnContext) -> Image.Image:
        return context.person_image.filter(ImageFilter.GaussianBlur(radius=10))

    def vram_estimate_mb(self) -> int:
        return 0
