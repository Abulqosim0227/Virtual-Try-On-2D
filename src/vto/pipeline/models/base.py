from abc import ABC, abstractmethod

from PIL import Image

from vto.pipeline.context import TryOnContext


class BaseVTOModel(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def load(self) -> None: ...

    @abstractmethod
    def unload(self) -> None: ...

    @abstractmethod
    def generate(self, context: TryOnContext) -> Image.Image: ...

    @abstractmethod
    def vram_estimate_mb(self) -> int: ...
