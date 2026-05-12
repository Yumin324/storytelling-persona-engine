import base64
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.errors import ProviderError
from app.services.provider_base import ProviderService, ensure_output_path


class OpenAIImageService(ProviderService):
    provider_name = "openai"
    image_generation_url = "https://api.openai.com/v1/images/generations"
    image_edit_url = "https://api.openai.com/v1/images/edits"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def generate_image(
        self,
        prompt: str,
        input_images: list[str] | None,
        output_path: str,
        db: Session | None = None,
        size: str | None = None,
    ) -> str:
        operation = "generate_image"
        target_path = ensure_output_path(output_path)

        async def call_openai() -> str:
            self._require_key(self.settings.openai_api_key, "OPENAI_API_KEY", operation)
            try:
                async with httpx.AsyncClient(timeout=self.settings.api_timeout_image_seconds) as client:
                    if input_images:
                        response = await self._create_image_edit(client, prompt, input_images, size=size)
                    else:
                        payload = {
                            "model": self.settings.openai_image_model,
                            "prompt": prompt,
                            "n": 1,
                            "output_format": "png",
                        }
                        if size:
                            payload["size"] = size
                        response = await client.post(self.image_generation_url, headers=self._headers(), json=payload)
                self._raise_for_response(response, operation)
                await self._save_image_response(response.json(), target_path, operation)
                return str(target_path)
            except httpx.TimeoutException as exc:
                raise ProviderError(
                    provider=self.provider_name,
                    operation=operation,
                    message=f"OpenAI image generation timed out after {self.settings.api_timeout_image_seconds} seconds.",
                    retryable=True,
                    raw_error_summary=str(exc),
                ) from exc
            except httpx.HTTPError as exc:
                raise ProviderError(
                    provider=self.provider_name,
                    operation=operation,
                    message="OpenAI image request failed before receiving a valid response.",
                    retryable=True,
                    raw_error_summary=str(exc),
                ) from exc

        return await self._with_retries(
            operation=operation,
            db=db,
            request_summary={
                "model": self.settings.openai_image_model,
                "has_input_images": bool(input_images),
                "output_path": str(target_path),
                "size": size,
            },
            func=call_openai,
            retries=self.settings.api_retry_count,
            backoff_seconds=(5, 15, 30),
        )

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.settings.openai_api_key}"}

    async def _create_image_edit(
        self,
        client: httpx.AsyncClient,
        prompt: str,
        input_images: list[str],
        size: str | None = None,
    ) -> httpx.Response:
        files = []
        opened_files = []
        try:
            for image_path in input_images:
                path = Path(image_path)
                opened = path.open("rb")
                opened_files.append(opened)
                files.append(("image[]", (path.name, opened, image_content_type(path))))

            data = {
                "model": self.settings.openai_image_model,
                "prompt": prompt,
                "n": "1",
                "output_format": "png",
            }
            if size:
                data["size"] = size
            return await client.post(self.image_edit_url, headers=self._headers(), data=data, files=files)
        finally:
            for opened in opened_files:
                opened.close()

    async def _save_image_response(self, data: dict[str, Any], output_path: Path, operation: str) -> None:
        images = data.get("data")
        if not images or not isinstance(images, list):
            raise ProviderError(
                provider=self.provider_name,
                operation=operation,
                message="OpenAI image response did not include image data.",
                retryable=False,
                raw_error_summary=str(data)[:500],
            )

        first = images[0]
        b64_json = first.get("b64_json")
        if b64_json:
            output_path.write_bytes(base64.b64decode(b64_json))
            return

        image_url = first.get("url")
        if image_url:
            async with httpx.AsyncClient(timeout=self.settings.api_timeout_image_seconds) as client:
                response = await client.get(image_url)
            self._raise_for_response(response, operation)
            output_path.write_bytes(response.content)
            return

        raise ProviderError(
            provider=self.provider_name,
            operation=operation,
            message="OpenAI image response contained neither base64 data nor a downloadable URL.",
            retryable=False,
            raw_error_summary=str(first)[:500],
        )


def image_content_type(path: Path) -> str:
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(path.suffix.lower(), "image/png")
