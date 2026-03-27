from datetime import datetime

from fastapi import APIRouter, Depends, Request

from vto.api.deps import require_api_key
from vto.api.schemas.common import APIResponse
from vto.api.schemas.jobs import JobStatusResponse

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/jobs/{job_id}")
async def get_job_status(
    request: Request,
    job_id: str,
) -> APIResponse:
    jobs = request.app.state.jobs
    job = jobs.get(job_id)

    if job is None:
        return APIResponse.fail("NOT_FOUND", f"Job {job_id} not found")

    if job["status"] == "failed":
        return APIResponse.fail("INFERENCE_TIMEOUT", job.get("error", "Job failed"))

    expires_at = None
    if job.get("expires_at"):
        expires_at = datetime.fromisoformat(job["expires_at"])

    return APIResponse.ok(
        JobStatusResponse(
            job_id=job_id,
            status=job["status"],
            result_url=job.get("result_url"),
            tier=job.get("tier"),
            model=job.get("model"),
            cached=job.get("cached"),
            processing_ms=job.get("processing_ms"),
            expires_at=expires_at,
        ).model_dump()
    )
