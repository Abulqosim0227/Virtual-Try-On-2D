import io
import time

import structlog

from vto.core.cache import ResultCache
from vto.core.storage import ResultStorage
from vto.core.vram_manager import VRAMManager
from vto.pipeline.context import TryOnContext

logger = structlog.get_logger()

TIER_MODEL_MAP = {
    "fast": "catvton",
    "hd": "idm_vton",
}


class Router:
    def __init__(
        self,
        vram_manager: VRAMManager,
        cache: ResultCache,
        storage: ResultStorage,
    ) -> None:
        self._vram = vram_manager
        self._cache = cache
        self._storage = storage

    async def handle(self, context: TryOnContext) -> dict:
        t_start = time.monotonic()

        cached = self._cache.get(context.cache_key)
        if cached is not None:
            context.timings["total"] = time.monotonic() - t_start
            logger.info("cache_hit", key=context.cache_key[:16])
            return self._build_result(context, cached, from_cache=True)

        try:
            context = self._run_preprocessing(context)
            result_bytes = await self._run_inference(context)
            self._cache.set(context.cache_key, result_bytes)
        finally:
            self._vram.cleanup()

        context.timings["total"] = time.monotonic() - t_start
        return self._build_result(context, result_bytes, from_cache=False)

    def _run_preprocessing(self, context: TryOnContext) -> TryOnContext:
        t = time.monotonic()
        for preprocessor in self._vram.preprocessors:
            context = preprocessor.process(context)
        context.timings["preprocessing"] = time.monotonic() - t
        return context

    async def _run_inference(self, context: TryOnContext) -> bytes:
        model_name = TIER_MODEL_MAP.get(context.tier, "catvton")

        t = time.monotonic()
        model = await self._vram.ensure_loaded(model_name)
        context.timings["model_swap"] = time.monotonic() - t

        t = time.monotonic()
        context.result_image = model.generate(context)
        context.model_used = model.name
        context.timings["inference"] = time.monotonic() - t

        buf = io.BytesIO()
        context.result_image.save(buf, format="JPEG", quality=95)
        return buf.getvalue()

    def _build_result(self, context: TryOnContext, image_bytes: bytes, from_cache: bool) -> dict:
        filename = f"{context.cache_key[:16]}_{context.tier}.jpg"
        self._storage.save(context.result_image or _bytes_to_image(image_bytes), filename)

        processing_ms = int(context.timings.get("total", 0) * 1000)

        logger.info(
            "request_complete",
            tier=context.tier,
            model=context.model_used,
            cached=from_cache,
            processing_ms=processing_ms,
            vram_mb=self._vram.get_vram_used_mb(),
        )

        return {
            "filename": filename,
            "tier": context.tier,
            "model": context.model_used or "cached",
            "cached": from_cache,
            "processing_ms": processing_ms,
            "timings": context.timings,
        }


def _bytes_to_image(image_bytes: bytes):
    from PIL import Image
    return Image.open(io.BytesIO(image_bytes))
