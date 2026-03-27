from datetime import datetime

from pydantic import BaseModel


class TryOnFastResponse(BaseModel):
    result_url: str
    tier: str
    model: str
    cached: bool
    processing_ms: int
    expires_at: datetime


class TryOnHDResponse(BaseModel):
    job_id: str
    status: str
    estimated_seconds: int
