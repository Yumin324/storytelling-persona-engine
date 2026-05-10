from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.errors import ProviderError
from app.services.provider_base import ProviderService, ensure_output_path


class ElevenLabsVoiceService(ProviderService):
    provider_name = "elevenlabs"
    base_url = "https://api.elevenlabs.io/v1"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def list_voices(self, db: Session | None = None) -> list[dict[str, Any]]:
        operation = "list_voices"

        async def call_elevenlabs() -> list[dict[str, Any]]:
            self._require_key(self.settings.elevenlabs_api_key, "ELEVENLABS_API_KEY", operation)
            try:
                async with httpx.AsyncClient(timeout=self.settings.api_timeout_voice_seconds) as client:
                    response = await client.get(f"{self.base_url}/voices", headers=self._headers())
                self._raise_for_response(response, operation)
                voices = response.json().get("voices", [])
                if not isinstance(voices, list):
                    raise ProviderError(
                        provider=self.provider_name,
                        operation=operation,
                        message="ElevenLabs voices response was not a list.",
                        retryable=False,
                        raw_error_summary=response.text[:500],
                    )
                return [self._normalize_voice(voice) for voice in voices]
            except httpx.TimeoutException as exc:
                raise ProviderError(
                    provider=self.provider_name,
                    operation=operation,
                    message=f"ElevenLabs voice listing timed out after {self.settings.api_timeout_voice_seconds} seconds.",
                    retryable=True,
                    raw_error_summary=str(exc),
                ) from exc
            except httpx.HTTPError as exc:
                raise ProviderError(
                    provider=self.provider_name,
                    operation=operation,
                    message="ElevenLabs voice listing failed before receiving a valid response.",
                    retryable=True,
                    raw_error_summary=str(exc),
                ) from exc

        return await self._with_retries(
            operation=operation,
            db=db,
            request_summary={"operation": operation},
            func=call_elevenlabs,
            retries=self.settings.api_retry_count,
        )

    async def text_to_speech(
        self,
        voice_id: str,
        text: str,
        voice_prompt: str,
        output_path: str,
        db: Session | None = None,
    ) -> str:
        operation = "text_to_speech"
        target_path = ensure_output_path(output_path)

        async def call_elevenlabs() -> str:
            self._require_key(self.settings.elevenlabs_api_key, "ELEVENLABS_API_KEY", operation)
            try:
                payload = {
                    "text": text,
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                        "style": 0.2,
                        "use_speaker_boost": True,
                    },
                    "apply_text_normalization": "auto",
                }
                if self.settings.elevenlabs_default_model:
                    payload["model_id"] = self.settings.elevenlabs_default_model

                async with httpx.AsyncClient(timeout=self.settings.api_timeout_voice_seconds) as client:
                    response = await client.post(
                        f"{self.base_url}/text-to-speech/{voice_id}",
                        params={"output_format": "mp3_44100_128"},
                        headers=self._headers() | {"Content-Type": "application/json"},
                        json=payload,
                    )
                self._raise_for_response(response, operation)
                self._save_audio_response(response, target_path, operation)
                return str(target_path)
            except httpx.TimeoutException as exc:
                raise ProviderError(
                    provider=self.provider_name,
                    operation=operation,
                    message=f"ElevenLabs text-to-speech timed out after {self.settings.api_timeout_voice_seconds} seconds.",
                    retryable=True,
                    raw_error_summary=str(exc),
                ) from exc
            except httpx.HTTPError as exc:
                raise ProviderError(
                    provider=self.provider_name,
                    operation=operation,
                    message="ElevenLabs text-to-speech failed before receiving a valid response.",
                    retryable=True,
                    raw_error_summary=str(exc),
                ) from exc

        return await self._with_retries(
            operation=operation,
            db=db,
            request_summary={
                "voice_id": voice_id,
                "output_path": str(target_path),
                "text_length": len(text),
                "voice_prompt_present": bool(voice_prompt),
            },
            func=call_elevenlabs,
            retries=self.settings.api_retry_count,
        )

    def _headers(self) -> dict[str, str]:
        return {"xi-api-key": self.settings.elevenlabs_api_key}

    @staticmethod
    def _normalize_voice(voice: dict[str, Any]) -> dict[str, Any]:
        labels = voice.get("labels") or {}
        return {
            "voice_id": voice.get("voice_id"),
            "name": voice.get("name"),
            "provider": "elevenlabs",
            "category": voice.get("category"),
            "description": voice.get("description"),
            "labels": labels,
            "gender": labels.get("gender") or labels.get("Gender"),
            "preview_url": voice.get("preview_url"),
        }

    def _save_audio_response(self, response: httpx.Response, output_path: Path, operation: str) -> None:
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            raise ProviderError(
                provider=self.provider_name,
                operation=operation,
                message="ElevenLabs returned JSON instead of MP3 audio.",
                retryable=False,
                raw_error_summary=response.text[:500],
            )
        if not response.content:
            raise ProviderError(
                provider=self.provider_name,
                operation=operation,
                message="ElevenLabs returned an empty audio response.",
                retryable=False,
            )
        output_path.write_bytes(response.content)
