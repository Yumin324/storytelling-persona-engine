import base64
import hashlib
import hmac
import json
import time
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.errors import ProviderError
from app.models import Status
from app.services.provider_base import ProviderService, ensure_output_path


class KlingVideoService(ProviderService):
    provider_name = "kling"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def create_video_task(
        self,
        image_path: str,
        prompt: str,
        db: Session | None = None,
    ) -> str:
        operation = "create_video_task"

        async def call_kling() -> str:
            self._require_auth(operation)
            if not self.settings.kling_api_base_url:
                raise ProviderError(
                    provider=self.provider_name,
                    operation=operation,
                    message="KLING_API_BASE_URL is missing. Add the Kling API base URL to backend/.env.",
                    retryable=False,
                    raw_error_summary="Missing required environment variable: KLING_API_BASE_URL",
                )
            try:
                async with httpx.AsyncClient(timeout=self.settings.api_timeout_video_create_seconds) as client:
                    response = await client.post(
                        self._url(self._create_task_path()),
                        headers=self._headers() | {"Content-Type": "application/json"},
                        json=self._create_task_payload(image_path, prompt),
                    )
                self._raise_for_response(response, operation)
                return self._extract_task_id(response.json(), operation)
            except httpx.TimeoutException as exc:
                raise ProviderError(
                    provider=self.provider_name,
                    operation=operation,
                    message=(
                        "Kling video task creation timed out after "
                        f"{self.settings.api_timeout_video_create_seconds} seconds."
                    ),
                    retryable=True,
                    raw_error_summary=str(exc),
                ) from exc
            except httpx.HTTPError as exc:
                raise ProviderError(
                    provider=self.provider_name,
                    operation=operation,
                    message="Kling video task creation failed before receiving a valid response.",
                    retryable=True,
                    raw_error_summary=str(exc),
                ) from exc

        return await self._with_retries(
            operation=operation,
            db=db,
            request_summary={"model": self._model_name(), "image_path": image_path},
            func=call_kling,
            retries=self.settings.api_retry_count,
        )

    async def poll_video_task(
        self,
        task_id: str,
        output_path: str,
        db: Session | None = None,
    ) -> str:
        operation = "poll_video_task"
        target_path = ensure_output_path(output_path)
        started = time.perf_counter()

        try:
            self._require_auth(operation)
            if not self.settings.kling_api_base_url:
                raise ProviderError(
                    provider=self.provider_name,
                    operation=operation,
                    message="KLING_API_BASE_URL is missing. Add the Kling API base URL to backend/.env.",
                    retryable=False,
                    raw_error_summary="Missing required environment variable: KLING_API_BASE_URL",
                )
            async with httpx.AsyncClient(timeout=self.settings.api_timeout_video_create_seconds) as client:
                while time.perf_counter() - started < self.settings.api_timeout_video_poll_total_seconds:
                    try:
                        response = await client.get(self._url(self._poll_task_path(task_id)), headers=self._headers())
                        self._raise_for_response(response, operation)
                    except (httpx.TimeoutException, httpx.HTTPError):
                        await asyncio_sleep(10)
                        continue

                    data = response.json()
                    status = self._extract_status(data)

                    if status in {"completed", "succeeded", "succeed", "success"}:
                        video_url = self._extract_video_url(data, operation)
                        await self._download_video(client, video_url, target_path, operation)
                        self._log_call(
                            db=db,
                            operation=operation,
                            status=Status.completed,
                            request_summary={"task_id": task_id, "output_path": str(target_path)},
                            response_summary={"provider_status": status},
                            duration_ms=self._duration_ms(started),
                        )
                        return str(target_path)

                    if status in {"failed", "fail", "error", "cancelled"}:
                        raise ProviderError(
                            provider=self.provider_name,
                            operation=operation,
                            message=f"Kling video task ended with status '{status}'.",
                            retryable=False,
                            raw_error_summary=str(data)[:500],
                        )

                    await asyncio_sleep(10)

            raise ProviderError(
                provider=self.provider_name,
                operation=operation,
                message=(
                    "Kling video polling timed out after "
                    f"{self.settings.api_timeout_video_poll_total_seconds} seconds."
                ),
                retryable=True,
                raw_error_summary=f"Task id: {task_id}",
            )
        except httpx.TimeoutException as exc:
            error = ProviderError(
                provider=self.provider_name,
                operation=operation,
                message="Kling polling request timed out while checking task status.",
                retryable=True,
                raw_error_summary=str(exc),
            )
            self._log_poll_failure(db, operation, task_id, target_path, started, error)
            raise error from exc
        except httpx.HTTPError as exc:
            error = ProviderError(
                provider=self.provider_name,
                operation=operation,
                message="Kling polling request failed before receiving a valid response.",
                retryable=True,
                raw_error_summary=str(exc),
            )
            self._log_poll_failure(db, operation, task_id, target_path, started, error)
            raise error from exc
        except ProviderError as exc:
            self._log_poll_failure(db, operation, task_id, target_path, started, exc)
            raise

    def _url(self, path: str) -> str:
        return f"{self.settings.kling_api_base_url.rstrip('/')}{path}"

    def _create_task_path(self) -> str:
        if self._is_omni_model():
            return "/v1/videos/omni-video"
        return "/v1/videos/image2video"

    def _poll_task_path(self, task_id: str) -> str:
        if self._is_omni_model():
            return f"/v1/videos/omni-video/{task_id}"
        return f"/v1/videos/image2video/{task_id}"

    def _create_task_payload(self, image_path: str, prompt: str) -> dict[str, Any]:
        model_name = self._model_name()
        payload = {
            "model_name": model_name,
            "prompt": prompt,
            "duration": "8",
            "mode": self._mode(),
            "sound": "off",
        }
        if self._is_omni_model():
            payload["multi_shot"] = False
            payload["image_list"] = [
                {
                    "image_url": self._image_base64(image_path),
                    "type": "first_frame",
                },
            ]
            return payload

        payload["image"] = self._image_base64(image_path)
        return payload

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_token()}"}

    def _require_auth(self, operation: str) -> None:
        if self.settings.kling_access_key and self.settings.kling_secret_key:
            return
        self._require_key(self.settings.kling_api_key, "KLING_API_KEY", operation)

    def _api_token(self) -> str:
        if self.settings.kling_access_key and self.settings.kling_secret_key:
            return self._jwt_token(self.settings.kling_access_key, self.settings.kling_secret_key)
        return self.settings.kling_api_key

    @staticmethod
    def _jwt_token(access_key: str, secret_key: str) -> str:
        now = int(time.time())
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "iss": access_key,
            "exp": now + 1800,
            "nbf": now - 5,
        }
        signing_input = ".".join(
            [
                base64_urlencode(json.dumps(header, separators=(",", ":")).encode("utf-8")),
                base64_urlencode(json.dumps(payload, separators=(",", ":")).encode("utf-8")),
            ],
        )
        signature = hmac.new(secret_key.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
        return f"{signing_input}.{base64_urlencode(signature)}"

    def _model_name(self) -> str:
        aliases = {
            "kling-3.0": "kling-v3",
            "kling3.0": "kling-v3",
            "kling-v3-0": "kling-v3",
            "kling-omni-3": "kling-v3-omni",
            "kling-3.0-omni": "kling-v3-omni",
            "kling-omni-3.0": "kling-v3-omni",
        }
        configured = self.settings.kling_video_model.strip()
        return aliases.get(configured.lower(), configured)

    def _mode(self) -> str:
        return "std" if "std" in self.settings.kling_video_model.lower() else "pro"

    def _is_omni_model(self) -> bool:
        return self._model_name() in {"kling-v3-omni", "kling-video-o1"}

    @staticmethod
    def _image_base64(image_path: str) -> str:
        return base64.b64encode(Path(image_path).read_bytes()).decode("ascii")

    def _extract_task_id(self, data: dict[str, Any], operation: str) -> str:
        task_id = data.get("task_id") or data.get("id") or data.get("data", {}).get("task_id")
        if not task_id:
            raise ProviderError(
                provider=self.provider_name,
                operation=operation,
                message="Kling response did not include a video task ID.",
                retryable=False,
                raw_error_summary=str(data)[:500],
            )
        return str(task_id)

    @staticmethod
    def _extract_status(data: dict[str, Any]) -> str:
        status = (
            data.get("status")
            or data.get("data", {}).get("status")
            or data.get("data", {}).get("task_status")
            or data.get("task_status")
        )
        return str(status or "running").lower()

    def _extract_video_url(self, data: dict[str, Any], operation: str) -> str:
        videos = data.get("data", {}).get("task_result", {}).get("videos")
        if isinstance(videos, list):
            for video in videos:
                if isinstance(video, dict) and video.get("url"):
                    return str(video["url"])

        response_urls = data.get("data", {}).get("response")
        if isinstance(response_urls, list):
            for response_url in response_urls:
                if response_url:
                    return str(response_url)

        candidates = [
            data.get("video_url"),
            data.get("url"),
            data.get("data", {}).get("video_url"),
            data.get("data", {}).get("url"),
            data.get("data", {}).get("result", {}).get("video_url"),
        ]
        for candidate in candidates:
            if candidate:
                return str(candidate)
        raise ProviderError(
            provider=self.provider_name,
            operation=operation,
            message="Kling completed task did not include a downloadable video URL.",
            retryable=False,
            raw_error_summary=str(data)[:500],
        )

    async def _download_video(
        self,
        client: httpx.AsyncClient,
        video_url: str,
        output_path: Path,
        operation: str,
    ) -> None:
        response = await client.get(video_url)
        self._raise_for_response(response, operation)
        output_path.write_bytes(response.content)

    def _log_poll_failure(
        self,
        db: Session | None,
        operation: str,
        task_id: str,
        output_path: Path,
        started: float,
        error: ProviderError,
    ) -> None:
        self._log_call(
            db=db,
            operation=operation,
            status=Status.failed,
            request_summary={"task_id": task_id, "output_path": str(output_path)},
            response_summary={
                "provider": error.provider,
                "operation": error.operation,
                "status": "failed",
                "message": error.message,
                "retryable": error.retryable,
                "raw_error_summary": error.raw_error_summary,
            },
            status_code=error.status_code,
            duration_ms=self._duration_ms(started),
            error_message=error.message,
        )


async def asyncio_sleep(seconds: int) -> None:
    import asyncio

    await asyncio.sleep(seconds)


def base64_urlencode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")
