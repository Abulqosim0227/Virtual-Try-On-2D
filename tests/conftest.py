import io
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from vto.config import settings
from vto.core.cache import ResultCache
from vto.core.router import Router, TIER_MODEL_MAP
from vto.core.storage import ResultStorage
from vto.core.vram_manager import VRAMManager
from vto.pipeline.models.mock import MockVTOModel


def _create_test_app():
    from vto.api.exceptions import VTOBaseError
    from vto.api.routes import garments, health, jobs, tryon
    from vto.api.schemas.common import APIResponse
    from vto.main import ERROR_STATUS_MAP
    from fastapi import Request
    from fastapi.responses import JSONResponse

    @asynccontextmanager
    async def test_lifespan(app: FastAPI):
        yield

    test_app = FastAPI(lifespan=test_lifespan)

    @test_app.exception_handler(VTOBaseError)
    async def vto_error_handler(request: Request, exc: VTOBaseError) -> JSONResponse:
        status_code = ERROR_STATUS_MAP.get(type(exc), 500)
        body = APIResponse.fail(exc.error_code, exc.message).model_dump()
        return JSONResponse(status_code=status_code, content=body)

    test_app.include_router(health.router, prefix="/v1")
    test_app.include_router(tryon.router, prefix="/v1")
    test_app.include_router(jobs.router, prefix="/v1")
    test_app.include_router(garments.router, prefix="/v1")

    return test_app


@pytest.fixture()
def vram_manager():
    manager = VRAMManager()
    mock_model = MockVTOModel()
    manager.register_model(mock_model)
    return manager


@pytest.fixture()
def cache():
    return ResultCache()


@pytest.fixture()
def storage(tmp_path):
    settings.results_dir = tmp_path
    return ResultStorage()


@pytest.fixture()
def test_client(vram_manager, cache, storage):
    app = _create_test_app()

    app.state.vram_manager = vram_manager
    app.state.cache = cache
    app.state.storage = storage
    app.state.router = Router(vram_manager, cache, storage)
    app.state.jobs = {}
    app.state.garments = {}

    original_fast = TIER_MODEL_MAP["fast"]
    original_hd = TIER_MODEL_MAP["hd"]
    TIER_MODEL_MAP["fast"] = "mock"
    TIER_MODEL_MAP["hd"] = "mock"

    with TestClient(app) as client:
        yield client

    TIER_MODEL_MAP["fast"] = original_fast
    TIER_MODEL_MAP["hd"] = original_hd


@pytest.fixture()
def auth_headers():
    return {"X-API-Key": settings.api_key}


@pytest.fixture()
def sample_image_bytes():
    img = Image.new("RGB", (200, 300), (180, 140, 100))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture()
def sample_png_bytes():
    img = Image.new("RGB", (200, 300), (100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
