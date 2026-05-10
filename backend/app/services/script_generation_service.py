from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import AdSession, Persona
from app.services.compliance_service import ComplianceService
from app.services.openai_llm_service import OpenAILLMService
from app.services.prompt_renderer import PromptRenderer


def build_script_prompt_context(session: AdSession, persona: Persona) -> dict[str, Any]:
    product = session.product_json or {}
    return {
        "persona": {
            "id": persona.id,
            "name": persona.name,
            "age": persona.age,
            "gender": persona.gender,
            "physical": persona.physical_json,
            "voice": persona.voice_json,
            "personality": persona.personality_json,
            "summary": f"{persona.name} - {persona.personality_json.get('content_niche', '')}",
        },
        "session": {
            "id": session.id,
            "outfit": session.outfit or "",
            "accessories": session.accessories_json,
        },
        "environment": session.environment_json or {},
        "product": product,
        "script": session.script_json or {},
        "scene": {},
        "meta": {"timestamp": datetime.now(timezone.utc).isoformat()},
    }


async def generate_compliant_script(db: Session, session: AdSession) -> dict[str, Any]:
    persona = db.get(Persona, session.persona_id)
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona not found.")

    product = session.product_json or {}
    expected_scene_count = int(product.get("number_of_scenes") or 0)
    validate_script_inputs(product, expected_scene_count)

    prompt = PromptRenderer().render_template("script_writer.md", build_script_prompt_context(session, persona))
    llm = OpenAILLMService()
    compliance = ComplianceService()

    script = await llm.generate_script(prompt, db=db)
    errors = compliance.validate_script(script, expected_scene_count)
    if not errors:
        return script

    repair_prompt = build_repair_prompt(prompt, script, errors, expected_scene_count)
    repaired_script = await llm.generate_script(repair_prompt, db=db)
    repaired_errors = compliance.validate_script(repaired_script, expected_scene_count)
    if repaired_errors:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Generated script failed compliance validation after one repair attempt.",
                "errors": repaired_errors,
            },
        )
    return repaired_script


def validate_script_inputs(product: dict[str, Any], expected_scene_count: int) -> None:
    if expected_scene_count < 3 or expected_scene_count > 10:
        raise HTTPException(status_code=422, detail="Number of scenes must be between 3 and 10.")
    for key, label in (
        ("name", "Product name"),
        ("category", "Product category"),
        ("key_benefits", "Key benefits"),
        ("target_audience", "Target audience"),
        ("cta", "Call to action"),
    ):
        if not product.get(key):
            raise HTTPException(status_code=422, detail=f"{label} is required before generating a script.")


def build_repair_prompt(original_prompt: str, invalid_script: dict[str, Any], errors: list[str], expected_scene_count: int) -> str:
    return (
        f"{original_prompt}\n\n"
        "The previous JSON failed backend compliance validation. Repair it once and return strict JSON only.\n"
        f"Expected scene count: {expected_scene_count}\n"
        f"Validation errors: {errors}\n"
        f"Invalid script JSON: {invalid_script}\n"
        "Keep the same product and persona context. Remove testimonial or first-person product experience language. "
        "Every voiceover must be 16 words or fewer. The CTA may appear only in the final scene."
    )
