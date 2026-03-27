from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from vto.api.exceptions import (
    InvalidInputError,
    ModelLoadError,
    PreprocessingError,
    VRAMExhaustedError,
    VTOBaseError,
    WorkerTimeoutError,
)
from vto.api.routes import garments, health, jobs, tryon
from vto.api.schemas.common import APIResponse
from vto.core.cache import ResultCache
from vto.core.router import Router
from vto.core.storage import ResultStorage
from vto.core.vram_manager import VRAMManager

logger = structlog.get_logger()

ERROR_STATUS_MAP = {
    InvalidInputError: 400,
    PreprocessingError: 422,
    VRAMExhaustedError: 503,
    WorkerTimeoutError: 504,
    ModelLoadError: 500,
}


def _register_models(vram_manager: VRAMManager) -> str:
    from vto.pipeline.models.mock import MockVTOModel

    vram_manager.register_model(MockVTOModel())

    try:
        from vto.pipeline.models.catvton import CatVTONModel
        model = CatVTONModel()
        vram_manager.register_model(model)
        vram_manager.load_default_model("catvton")
        logger.info("model_loaded", name="catvton", vram_mb=vram_manager.get_vram_used_mb())
        return "catvton"
    except Exception as e:
        logger.warning("catvton_unavailable", error=str(e))
        vram_manager.load_default_model("mock")
        logger.info("model_loaded", name="mock", fallback=True)
        return "mock"


@asynccontextmanager
async def lifespan(app: FastAPI):
    vram_manager = VRAMManager()
    cache = ResultCache()
    storage = ResultStorage()

    cache.connect()
    default_model = _register_models(vram_manager)

    from vto.core.router import TIER_MODEL_MAP
    TIER_MODEL_MAP["fast"] = default_model
    TIER_MODEL_MAP["hd"] = default_model

    app.state.vram_manager = vram_manager
    app.state.cache = cache
    app.state.storage = storage
    app.state.router = Router(vram_manager, cache, storage)
    app.state.jobs = {}
    app.state.garments = {}

    logger.info("app_started", model=default_model, vram_mb=vram_manager.get_vram_used_mb())
    yield

    if vram_manager.current_model_name:
        vram_manager.cleanup()
    logger.info("app_stopped")


app = FastAPI(
    title="Virtual Try-On API",
    version="0.1.0",
    docs_url="/v1/docs",
    openapi_url="/v1/openapi.json",
    lifespan=lifespan,
)

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from fastapi.staticfiles import StaticFiles
from vto.config import settings
import os
os.makedirs(settings.results_dir, exist_ok=True)
app.mount("/results", StaticFiles(directory=str(settings.results_dir)), name="results")


@app.exception_handler(VTOBaseError)
async def vto_error_handler(request: Request, exc: VTOBaseError) -> JSONResponse:
    status_code = ERROR_STATUS_MAP.get(type(exc), 500)
    body = APIResponse.fail(exc.error_code, exc.message).model_dump()
    return JSONResponse(status_code=status_code, content=body)


app.include_router(health.router, prefix="/v1")
app.include_router(tryon.router, prefix="/v1")
app.include_router(jobs.router, prefix="/v1")
app.include_router(garments.router, prefix="/v1")
