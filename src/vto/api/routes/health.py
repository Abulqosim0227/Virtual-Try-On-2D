import time

from fastapi import APIRouter, Request

router = APIRouter()

_start_time = time.monotonic()


@router.get("/health")
async def health(request: Request) -> dict:
    vram_manager = getattr(request.app.state, "vram_manager", None)
    cache = getattr(request.app.state, "cache", None)

    vram_used = 0
    vram_total = 0
    models_loaded: list[str] = []
    if vram_manager:
        vram_used = vram_manager.get_vram_used_mb()
        vram_total = vram_manager.get_vram_total_mb()
        models_loaded = vram_manager.loaded_names

    redis_connected = cache.connected if cache else False

    return {
        "status": "ok",
        "gpu_vram_used_mb": vram_used,
        "gpu_vram_total_mb": vram_total,
        "models_loaded": models_loaded,
        "redis_connected": redis_connected,
        "uptime_seconds": int(time.monotonic() - _start_time),
    }
