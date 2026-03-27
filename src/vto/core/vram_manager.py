import asyncio

import structlog
import torch

from vto.api.exceptions import ModelLoadError, VRAMExhaustedError
from vto.pipeline.models.base import BaseVTOModel
from vto.pipeline.preprocessors.base import BasePreprocessor

logger = structlog.get_logger()


class VRAMManager:
    def __init__(self) -> None:
        self._preprocessors: dict[str, BasePreprocessor] = {}
        self._models: dict[str, BaseVTOModel] = {}
        self._current_model: BaseVTOModel | None = None
        self._lock = asyncio.Lock()

    def register_preprocessor(self, preprocessor: BasePreprocessor) -> None:
        self._preprocessors[preprocessor.name] = preprocessor

    def register_model(self, model: BaseVTOModel) -> None:
        self._models[model.name] = model

    def load_preprocessors(self) -> None:
        for name, preprocessor in self._preprocessors.items():
            try:
                preprocessor.load()
                logger.info("preprocessor_loaded", name=name, vram_mb=preprocessor.vram_estimate_mb())
            except Exception as e:
                raise ModelLoadError(f"Failed to load preprocessor: {name} — {e}")

    def load_default_model(self, name: str) -> None:
        if name not in self._models:
            raise ModelLoadError(f"Unknown model: {name}")
        try:
            self._models[name].load()
            self._current_model = self._models[name]
            logger.info("model_loaded", name=name, vram_mb=self._current_model.vram_estimate_mb())
        except torch.cuda.OutOfMemoryError:
            raise VRAMExhaustedError(f"Not enough VRAM to load {name}")
        except Exception as e:
            raise ModelLoadError(f"Failed to load model: {name} — {e}")

    async def ensure_loaded(self, name: str) -> BaseVTOModel:
        async with self._lock:
            if self._current_model and self._current_model.name == name:
                return self._current_model

            if name not in self._models:
                raise ModelLoadError(f"Unknown model: {name}")

            if self._current_model:
                old_name = self._current_model.name
                self._current_model.unload()
                self.cleanup()
                logger.info("model_unloaded", name=old_name)

            try:
                self._models[name].load()
                self._current_model = self._models[name]
                logger.info(
                    "model_swapped",
                    name=name,
                    vram_mb=self._current_model.vram_estimate_mb(),
                    vram_used_mb=self.get_vram_used_mb(),
                )
            except torch.cuda.OutOfMemoryError:
                raise VRAMExhaustedError(f"Not enough VRAM to load {name}")
            except Exception as e:
                raise ModelLoadError(f"Failed to load model: {name} — {e}")

            return self._current_model

    @property
    def current_model_name(self) -> str | None:
        if self._current_model:
            return self._current_model.name
        return None

    @property
    def loaded_names(self) -> list[str]:
        names = [p.name for p in self._preprocessors.values()]
        if self._current_model:
            names.append(self._current_model.name)
        return names

    @property
    def preprocessors(self) -> list[BasePreprocessor]:
        return list(self._preprocessors.values())

    @staticmethod
    def get_vram_used_mb() -> int:
        if not torch.cuda.is_available():
            return 0
        return int(torch.cuda.memory_allocated() / (1024 * 1024))

    @staticmethod
    def get_vram_total_mb() -> int:
        if not torch.cuda.is_available():
            return 0
        return int(torch.cuda.get_device_properties(0).total_memory / (1024 * 1024))

    @staticmethod
    def cleanup() -> None:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        import gc
        gc.collect()
