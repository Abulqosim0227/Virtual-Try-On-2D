from typing import Any

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str


class APIResponse(BaseModel):
    success: bool
    data: Any | None = None
    error: ErrorDetail | None = None

    @staticmethod
    def ok(data: Any) -> "APIResponse":
        return APIResponse(success=True, data=data)

    @staticmethod
    def fail(code: str, message: str) -> "APIResponse":
        return APIResponse(success=False, error=ErrorDetail(code=code, message=message))
