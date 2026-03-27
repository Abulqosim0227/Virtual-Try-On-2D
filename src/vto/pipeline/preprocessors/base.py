from abc import ABC, abstractmethod

from vto.pipeline.context import TryOnContext


class BasePreprocessor(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def load(self) -> None: ...

    @abstractmethod
    def unload(self) -> None: ...

    @abstractmethod
    def process(self, context: TryOnContext) -> TryOnContext: ...

    @abstractmethod
    def vram_estimate_mb(self) -> int: ...
