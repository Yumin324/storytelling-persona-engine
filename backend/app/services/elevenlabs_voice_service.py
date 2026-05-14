from pathlib import Path
import re
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.errors import ProviderError
from app.services.provider_base import ProviderService, ensure_output_path


class ElevenLabsVoiceService(ProviderService):
    provider_name = "elevenlabs"
    base_url = "https://api.elevenlabs.io/v1"
    default_voice_settings = {
        "stability": 0.4,
        "similarity_boost": 0.75,
        "style": 0.55,
        "use_speaker_boost": True,
    }

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
        voice_settings: dict[str, Any] | None = None,
        db: Session | None = None,
    ) -> str:
        operation = "text_to_speech"
        target_path = ensure_output_path(output_path)
        speech_text = self._speech_text_with_expression(text, voice_prompt)
        expressive_prompt_used = speech_text != text
        resolved_voice_settings = self._voice_settings(voice_settings, expressive=expressive_prompt_used)

        async def call_elevenlabs() -> str:
            self._require_key(self.settings.elevenlabs_api_key, "ELEVENLABS_API_KEY", operation)
            try:
                payload = {
                    "text": speech_text,
                    "voice_settings": resolved_voice_settings,
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
                "text_length": len(speech_text),
                "voice_prompt_present": bool(voice_prompt),
                "voice_prompt_used": expressive_prompt_used,
                "voice_style": resolved_voice_settings["style"],
                "voice_stability": resolved_voice_settings["stability"],
            },
            func=call_elevenlabs,
            retries=self.settings.api_retry_count,
        )

    def _headers(self) -> dict[str, str]:
        return {"xi-api-key": self.settings.elevenlabs_api_key}

    @classmethod
    def _voice_settings(cls, voice_settings: dict[str, Any] | None, expressive: bool) -> dict[str, Any]:
        settings = dict(cls.default_voice_settings)
        if isinstance(voice_settings, dict):
            for key in ("stability", "similarity_boost", "style"):
                value = voice_settings.get(key)
                if isinstance(value, int | float):
                    settings[key] = cls._clamp_float(value)
            speaker_boost = voice_settings.get("use_speaker_boost")
            if isinstance(speaker_boost, bool):
                settings["use_speaker_boost"] = speaker_boost

        if expressive:
            settings["style"] = max(settings["style"], 0.55)
            settings["stability"] = min(settings["stability"], 0.45)
        return settings

    @staticmethod
    def _clamp_float(value: int | float) -> float:
        return max(0.0, min(float(value), 1.0))

    @classmethod
    def _speech_text_with_expression(cls, text: str, voice_prompt: str) -> str:
        clean_text = text.strip()
        clean_prompt = voice_prompt.strip()
        if not clean_prompt:
            return clean_text
        if cls._contains_words_in_order(clean_prompt, clean_text):
            return clean_prompt
        return clean_text

    @classmethod
    def _contains_words_in_order(cls, candidate: str, required_text: str) -> bool:
        required_words = cls._spoken_words(required_text)
        if not required_words:
            return False

        candidate_words = cls._spoken_words(cls._remove_audio_tags(candidate))
        search_from = 0
        for required_word in required_words:
            try:
                found_at = candidate_words.index(required_word, search_from)
            except ValueError:
                return False
            search_from = found_at + 1
        return True

    @staticmethod
    def _remove_audio_tags(text: str) -> str:
        return re.sub(r"\[[^\]]+\]", " ", text)

    @staticmethod
    def _spoken_words(text: str) -> list[str]:
        return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", text.casefold())

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
