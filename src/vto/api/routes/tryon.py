import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Form, Request, UploadFile

from vto.api.deps import require_api_key
from vto.api.schemas.common import APIResponse
from vto.api.schemas.tryon import TryOnFastResponse, TryOnHDResponse
from vto.config import settings
from vto.pipeline.runner import build_context

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.post("/tryon/fast")
async def tryon_fast(
    request: Request,
    person_image: UploadFile,
    garment_image: UploadFile,
    category: Literal["upper", "lower", "full"] = Form(default="upper"),
) -> APIResponse:
    person_bytes = await person_image.read()
    garment_bytes = await garment_image.read()

    context = build_context(person_bytes, garment_bytes, category, tier="fast")

    router_service = request.app.state.router
    result = await router_service.handle(context)

    storage = request.app.state.storage
    base_url = f"http://localhost:8899"
    result_url = storage.get_signed_url(result["filename"], base_url)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.result_ttl_hours)

    return APIResponse.ok(
        TryOnFastResponse(
            result_url=result_url,
            tier=result["tier"],
            model=result["model"],
            cached=result["cached"],
            processing_ms=result["processing_ms"],
            expires_at=expires_at,
        ).model_dump()
    )


@router.post("/tryon/hd")
async def tryon_hd(
    request: Request,
    person_image: UploadFile,
    garment_image: UploadFile,
    category: Literal["upper", "lower", "full"] = Form(default="upper"),
) -> APIResponse:
    person_bytes = await person_image.read()
    garment_bytes = await garment_image.read()

    context = build_context(person_bytes, garment_bytes, category, tier="hd")
    job_id = f"job_{uuid.uuid4().hex[:12]}"

    jobs = request.app.state.jobs
    jobs[job_id] = {"status": "processing", "context": context}

    router_service = request.app.state.router
    try:
        result = await router_service.handle(context)
        storage = request.app.state.storage
        base_url = f"http://localhost:8899"
        result_url = storage.get_signed_url(result["filename"], base_url)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.result_ttl_hours)

        jobs[job_id] = {
            "status": "completed",
            "result_url": result_url,
            "tier": result["tier"],
            "model": result["model"],
            "cached": result["cached"],
            "processing_ms": result["processing_ms"],
            "expires_at": expires_at.isoformat(),
        }
    except Exception as e:
        jobs[job_id] = {"status": "failed", "error": str(e)}
        raise

    return APIResponse.ok(
        TryOnHDResponse(
            job_id=job_id,
            status="completed",
            estimated_seconds=0,
        ).model_dump()
    )
