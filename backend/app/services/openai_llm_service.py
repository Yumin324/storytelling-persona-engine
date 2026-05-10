import json
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.errors import ProviderError
from app.services.provider_base import ProviderService


class OpenAILLMService(ProviderService):
    provider_name = "openai"
    responses_url = "https://api.openai.com/v1/responses"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def generate_script(self, payload: dict[str, Any] | str, db: Session | None = None) -> dict[str, Any]:
        return await self._generate_json(
            operation="generate_script",
            payload=payload,
            db=db,
            schema_name="ugclabs_script",
            json_schema={
                "type": "object",
                "additionalProperties": False,
                "required": ["persona_summary", "scenes"],
                "properties": {
                    "persona_summary": {"type": "string"},
                    "scenes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["scene_id", "visual", "voiceover"],
                            "properties": {
                                "scene_id": {"type": "string"},
                                "visual": {"type": "string"},
                                "voiceover": {"type": "string"},
                            },
                        },
                    },
                },
            },
        )

    async def generate_scene_prompts(self, payload: dict[str, Any] | str, db: Session | None = None) -> dict[str, Any]:
        return await self._generate_json(
            operation="generate_scene_prompts",
            payload=payload,
            db=db,
            schema_name="ugclabs_scene_prompts",
            json_schema={
                "type": "object",
                "additionalProperties": False,
                "required": ["scene_id", "image_prompt", "video_prompt", "voice_prompt", "safety_notes"],
                "properties": {
                    "scene_id": {"type": "string"},
                    "image_prompt": {"type": "string"},
                    "video_prompt": {"type": "string"},
                    "voice_prompt": {"type": "string"},
                    "safety_notes": {"type": "array", "items": {"type": "string"}},
                },
            },
        )

    async def _generate_json(
        self,
        *,
        operation: str,
        payload: dict[str, Any] | str,
        db: Session | None,
        schema_name: str,
        json_schema: dict[str, Any],
    ) -> dict[str, Any]:
        async def call_openai() -> dict[str, Any]:
            self._require_key(self.settings.openai_api_key, "OPENAI_API_KEY", operation)
            try:
                async with httpx.AsyncClient(timeout=self.settings.api_timeout_llm_seconds) as client:
                    response = await client.post(
                        self.responses_url,
                        headers=self._headers(),
                        json={
                            "model": self.settings.openai_llm_model,
                            "input": self._input(payload),
                            "text": {
                                "format": {
                                    "type": "json_schema",
                                    "name": schema_name,
                                    "strict": True,
                                    "schema": json_schema,
                                },
                            },
                        },
                    )
                self._raise_for_response(response, operation)
                return self._parse_json_response(response.json(), operation)
            except httpx.TimeoutException as exc:
                raise ProviderError(
                    provider=self.provider_name,
                    operation=operation,
                    message=f"OpenAI {operation} timed out after {self.settings.api_timeout_llm_seconds} seconds.",
                    retryable=True,
                    raw_error_summary=str(exc),
                ) from exc
            except httpx.HTTPError as exc:
                raise ProviderError(
                    provider=self.provider_name,
                    operation=operation,
                    message=f"OpenAI {operation} request failed before receiving a valid response.",
                    retryable=True,
                    raw_error_summary=str(exc),
                ) from exc

        return await self._with_retries(
            operation=operation,
            db=db,
            request_summary={"model": self.settings.openai_llm_model, "payload_type": type(payload).__name__},
            func=call_openai,
            retries=self.settings.api_retry_count,
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _input(payload: dict[str, Any] | str) -> str:
        if isinstance(payload, str):
            return payload
        return json.dumps(payload, ensure_ascii=False)

    def _parse_json_response(self, data: dict[str, Any], operation: str) -> dict[str, Any]:
        output_text = data.get("output_text")
        if not output_text:
            output_text = self._collect_output_text(data)
        if not output_text:
            raise ProviderError(
                provider=self.provider_name,
                operation=operation,
                message="OpenAI returned no JSON text output.",
                retryable=False,
                raw_error_summary=json.dumps(data)[:500],
            )

        try:
            parsed = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise ProviderError(
                provider=self.provider_name,
                operation=operation,
                message="OpenAI returned invalid JSON for a strict JSON operation.",
                retryable=False,
                raw_error_summary=output_text[:500],
            ) from exc

        if not isinstance(parsed, dict):
            raise ProviderError(
                provider=self.provider_name,
                operation=operation,
                message="OpenAI JSON output must be an object.",
                retryable=False,
                raw_error_summary=output_text[:500],
            )
        return parsed

    @staticmethod
    def _collect_output_text(data: dict[str, Any]) -> str:
        chunks: list[str] = []
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    chunks.append(content["text"])
        return "".join(chunks)
