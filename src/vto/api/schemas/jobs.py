from datetime import datetime

from pydantic import BaseModel


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result_url: str | None = None
    tier: str | None = None
    model: str | None = None
    cached: bool | None = None
    processing_ms: int | None = None
    expires_at: datetime | None = None
