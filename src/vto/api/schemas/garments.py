from pydantic import BaseModel


class GarmentResponse(BaseModel):
    garment_id: str
    category: str
    name: str | None = None
    image_url: str


class GarmentListResponse(BaseModel):
    garments: list[GarmentResponse]
    total: int
    page: int
    limit: int
