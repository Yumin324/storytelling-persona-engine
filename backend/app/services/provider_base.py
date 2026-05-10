import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any, TypeVar

import httpx
from sqlalchemy.orm import Session

from app.errors import ProviderError
from app.models import Status
from app.services.api_log_service import create_api_log

T = TypeVar("T")


DEFAULT_BACKOFF_SECONDS = (2, 5, 10)


class ProviderService:
    provider_name: str

    def _require_key(self, key: str, env_name: str, operation: str) -> None:
        if not key:
            raise ProviderError(
                provider=self.provider_name,
                operation=operation,
                message=f"{env_name} is missing. Add it to backend/.env before calling {self.provider_name}.",
                retryable=False,
                raw_error_summary=f"Missing required environment variable: {env_name}",
            )

    async def _with_retries(
        self,
        *,
        operation: str,
        db: Session | None,
        request_summary: dict[str, Any],
        func: Callable[[], Awaitable[T]],
        retries: int,
        backoff_seconds: tuple[int, ...] = DEFAULT_BACKOFF_SECONDS,
    ) -> T:
        started = time.perf_counter()
        last_error: ProviderError | None = None

        for attempt in range(1, retries + 1):
            try:
                result = await func()
                self._log_call(
                    db=db,
                    operation=operation,
                    status=Status.completed,
                    request_summary=request_summary | {"attempts": attempt},
                    response_summary={"ok": True},
                    duration_ms=self._duration_ms(started),
                )
                return result
            except ProviderError as exc:
                last_error = exc
                if not exc.retryable or attempt >= retries:
                    break
                await asyncio.sleep(backoff_seconds[min(attempt - 1, len(backoff_seconds) - 1)])

        assert last_error is not None
        self._log_call(
            db=db,
            operation=operation,
            status=Status.failed,
            request_summary=request_summary,
            response_summary=asdict(last_error.normalized()),
            status_code=last_error.status_code,
            duration_ms=self._duration_ms(started),
            error_message=last_error.message,
        )
        raise last_error

    def _log_call(
        self,
        *,
        db: Session | None,
        operation: str,
        status: Status,
        request_summary: dict[str, Any] | None = None,
        response_summary: dict[str, Any] | None = None,
        status_code: int | None = None,
        duration_ms: int | None = None,
        error_message: str | None = None,
    ) -> None:
        if db is None:
            return

        create_api_log(
            db,
            provider=self.provider_name,
            operation=operation,
            status=status,
            request_summary_json=self._safe_json(request_summary),
            response_summary_json=self._safe_json(response_summary),
            status_code=status_code,
            duration_ms=duration_ms,
            error_message=error_message,
        )

    @staticmethod
    def _duration_ms(started: float) -> int:
        return int((time.perf_counter() - started) * 1000)

    @staticmethod
    def _safe_json(value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return None
        return json.loads(json.dumps(value, default=str))

    def _raise_for_response(self, response: httpx.Response, operation: str) -> None:
        if response.status_code < 400:
            return

        retryable = response.status_code in {408, 409, 425, 429, 500, 502, 503, 504}
        raise ProviderError(
            provider=self.provider_name,
            operation=operation,
            message=self._provider_message(response, operation),
            retryable=retryable,
            raw_error_summary=response.text[:500],
            status_code=response.status_code,
        )

    def _provider_message(self, response: httpx.Response, operation: str) -> str:
        try:
            data = response.json()
        except ValueError:
            data = {}

        message = data.get("error", {}).get("message") if isinstance(data.get("error"), dict) else None
        return message or f"{self.provider_name} {operation} failed with HTTP {response.status_code}."


def ensure_output_path(output_path: str | Path) -> Path:
    path = Path(output_path)
    if path.name in {"", ".", ".."}:
        raise ProviderError(
            provider="storage",
            operation="write_output",
            message="Output path must point to a file.",
            retryable=False,
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
