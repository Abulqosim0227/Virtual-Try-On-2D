import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Form, Query, Request, UploadFile

from vto.api.deps import require_api_key
from vto.api.schemas.common import APIResponse
from vto.api.schemas.garments import GarmentListResponse, GarmentResponse
from vto.config import settings
from vto.core.normalizer import normalize_image

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.post("/garments", status_code=201)
async def upload_garment(
    request: Request,
    image: UploadFile,
    category: Literal["upper", "lower", "full"] = Form(default="upper"),
    name: str | None = Form(default=None),
) -> APIResponse:
    image_bytes = await image.read()
    normalized = normalize_image(image_bytes)

    garment_id = f"g_{uuid.uuid4().hex[:12]}"
    filename = f"{garment_id}.jpg"

    storage = request.app.state.storage
    storage.save(normalized, filename)

    base_url = f"http://{settings.app_host}:{settings.app_port}"
    image_url = f"{base_url}/garments/{filename}"

    garments = request.app.state.garments
    garments[garment_id] = {
        "garment_id": garment_id,
        "category": category,
        "name": name,
        "image_url": image_url,
        "filename": filename,
    }

    return APIResponse.ok(
        GarmentResponse(
            garment_id=garment_id,
            category=category,
            name=name,
            image_url=image_url,
        ).model_dump()
    )


@router.get("/garments")
async def list_garments(
    request: Request,
    category: Literal["upper", "lower", "full"] | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> APIResponse:
    garments = request.app.state.garments
    items = list(garments.values())

    if category:
        items = [g for g in items if g["category"] == category]

    total = len(items)
    start = (page - 1) * limit
    page_items = items[start : start + limit]

    return APIResponse.ok(
        GarmentListResponse(
            garments=[
                GarmentResponse(
                    garment_id=g["garment_id"],
                    category=g["category"],
                    name=g.get("name"),
                    image_url=g["image_url"],
                )
                for g in page_items
            ],
            total=total,
            page=page,
            limit=limit,
        ).model_dump()
    )


@router.delete("/garments/{garment_id}")
async def delete_garment(
    request: Request,
    garment_id: str,
) -> APIResponse:
    garments = request.app.state.garments

    if garment_id not in garments:
        return APIResponse.fail("NOT_FOUND", f"Garment {garment_id} not found")

    garment = garments.pop(garment_id)
    storage = request.app.state.storage
    storage.delete(garment["filename"])

    return APIResponse.ok({"deleted": garment_id})
