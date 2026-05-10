from typing import Any

from sqlalchemy.orm import Session

from app.models import ApiLog, Status


def create_api_log(
    db: Session,
    *,
    provider: str,
    operation: str,
    status: Status,
    related_type: str | None = None,
    related_id: int | None = None,
    request_summary_json: dict[str, Any] | None = None,
    response_summary_json: dict[str, Any] | None = None,
    status_code: int | None = None,
    duration_ms: int | None = None,
    error_message: str | None = None,
) -> ApiLog:
    api_log = ApiLog(
        provider=provider,
        operation=operation,
        related_type=related_type,
        related_id=related_id,
        request_summary_json=request_summary_json,
        response_summary_json=response_summary_json,
        status=status,
        status_code=status_code,
        duration_ms=duration_ms,
        error_message=error_message,
    )
    db.add(api_log)
    db.commit()
    db.refresh(api_log)
    return api_log
