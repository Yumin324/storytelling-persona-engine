from app.services.compliance_service import ComplianceService
from app.services.prompt_renderer import PromptRenderer


def sample_context() -> dict:
    return {
        "persona": {
            "id": 1,
            "name": "Ari",
            "age": 24,
            "gender": "Female",
            "summary": "Ari - skincare, tutorial, subtle humor",
            "physical": {
                "ethnicity": "South Asian",
                "skin_tone": "Medium",
                "face_shape": "Oval",
                "jawline": "Soft",
                "cheekbones": "Medium",
                "eye_shape": "Almond",
                "eye_color": "Dark Brown",
                "eyebrow_shape": "Curved",
                "eyebrow_color": "Dark Brown",
                "nose_shape": "Straight",
                "mouth_shape": "Medium",
                "lip_fullness": "Medium",
                "hair_length": "Long",
                "hair_texture": "Wavy",
                "default_hair_color": "Black",
                "facial_hair": "None",
                "body_type": "Average",
                "distinguishing_features": ["Dimples"],
            },
            "voice": {"voice_id": "voice_123"},
            "personality": {
                "core_personality": "Relatable",
                "content_niche": "Skincare",
                "communication_style": "Tutorial",
                "humor_level": "Subtle",
                "values": ["Authenticity"],
            },
        },
        "session": {
            "outfit": "white cotton shirt",
            "accessories": ["Earrings"],
        },
        "environment": {
            "primary_environment": "Bathroom",
            "time_of_day": "Morning",
            "lighting_style": "Natural light",
            "aesthetic": "Minimal clean",
        },
        "product": {
            "name": "Glow Serum",
            "category": "Skincare",
            "key_benefits": "lightweight hydration and smoother-looking texture",
            "target_audience": "busy students",
            "number_of_scenes": 5,
            "cta": "Shop now",
        },
        "scene": {
            "scene_id": "Scene 01",
            "visual": "Phone-shot close-up of product on bathroom counter.",
            "voiceover": "A simple hydration step can make a morning routine feel easier.",
            "product_revealed": True,
        },
        "meta": {"timestamp": "2026-05-10T00:00:00Z"},
    }


def test_prompt_renderer_replaces_placeholders():
    prompt = PromptRenderer().render_template("character_base.json", sample_context())

    assert "{{" not in prompt
    assert "Ari" in prompt
    assert "South Asian" in prompt


def test_compliance_catches_banned_phrase():
    service = ComplianceService()

    assert service.contains_banned_testimonial("I tried this and it changed my life.")


def test_script_json_shape_and_word_count_validation():
    service = ComplianceService()
    script = {
        "persona_summary": "Ari - skincare, tutorial, subtle humor",
        "scenes": [
            {
                "scene_id": "Scene 01",
                "visual": "Product bottle on counter.",
                "voiceover": "This simple serum brings lightweight hydration to rushed morning skincare routines.",
            },
            {
                "scene_id": "Scene 02",
                "visual": "Product texture close-up.",
                "voiceover": "Shop now for a smoother-looking routine with fewer complicated steps.",
            },
        ],
    }

    assert service.validate_script(script, expected_scene_count=2) == []

    script["scenes"][0]["voiceover"] = (
        "This serum is described with far too many words for an eight second voiceover and should be rejected."
    )
    errors = service.validate_script(script, expected_scene_count=2)
    assert any("maximum is 16" in error for error in errors)


def test_scene_prompt_json_shape_validation():
    service = ComplianceService()
    output = {
        "scene_id": "Scene 01",
        "image_prompt": "Phone-shot UGC first frame.",
        "video_prompt": "Slow handheld movement for 8 seconds.",
        "voice_prompt": "Natural clear delivery.",
        "safety_notes": ["No testimonial claims."],
    }

    assert service.validate_scene_prompt_output(output) == []

    output.pop("voice_prompt")
    errors = service.validate_scene_prompt_output(output)
    assert any("voice_prompt" in error for error in errors)
