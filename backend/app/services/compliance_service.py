import re
from typing import Any


BANNED_TESTIMONIAL_PHRASES = (
    "I tried",
    "I've tried",
    "I used",
    "I've used",
    "I started using",
    "my results",
    "my skin was",
    "my hair was",
    "changed my life",
    "saved me",
    "cured",
    "guaranteed",
    "miracle",
    "before I found",
    "I struggled with",
    "I was suffering",
)

WORD_PATTERN = re.compile(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)?")


class ComplianceService:
    @staticmethod
    def count_words(text: str) -> int:
        return len(WORD_PATTERN.findall(text or ""))

    @staticmethod
    def contains_banned_testimonial(text: str) -> bool:
        normalized = re.sub(r"\s+", " ", text or "").casefold()
        return any(phrase.casefold() in normalized for phrase in BANNED_TESTIMONIAL_PHRASES)

    def validate_script(self, script: dict[str, Any], expected_scene_count: int) -> list[str]:
        errors: list[str] = []

        if not isinstance(script, dict):
            return ["Script output must be a JSON object."]

        persona_summary = script.get("persona_summary")
        if not isinstance(persona_summary, str) or not persona_summary.strip():
            errors.append("Script must include a non-empty persona_summary.")

        scenes = script.get("scenes")
        if not isinstance(scenes, list):
            errors.append("Script must include a scenes list.")
            return errors

        if len(scenes) != expected_scene_count:
            errors.append(f"Script must include exactly {expected_scene_count} scenes.")

        cta_count = 0
        for index, scene in enumerate(scenes, start=1):
            label = f"Scene {index:02d}"
            if not isinstance(scene, dict):
                errors.append(f"{label} must be a JSON object.")
                continue

            scene_id = scene.get("scene_id")
            visual = scene.get("visual")
            voiceover = scene.get("voiceover")

            if not isinstance(scene_id, str) or not scene_id.strip():
                errors.append(f"{label} must include scene_id.")
            if not isinstance(visual, str) or not visual.strip():
                errors.append(f"{label} must include visual.")
            if not isinstance(voiceover, str) or not voiceover.strip():
                errors.append(f"{label} must include voiceover.")
                continue

            word_count = self.count_words(voiceover)
            if word_count > 16:
                errors.append(f"{label} voiceover has {word_count} words; maximum is 16.")
            if self.contains_banned_testimonial(voiceover):
                errors.append(f"{label} voiceover contains banned testimonial language.")
            if self.contains_banned_testimonial(visual):
                errors.append(f"{label} visual contains banned testimonial language.")

            if self._contains_cta(voiceover):
                cta_count += 1
                if index != len(scenes):
                    errors.append("CTA language should appear only in the final scene.")

        if cta_count > 1:
            errors.append("CTA language appears more than once.")

        return errors

    def validate_scene_prompt_output(self, output: dict[str, Any]) -> list[str]:
        errors: list[str] = []

        if not isinstance(output, dict):
            return ["Scene prompt output must be a JSON object."]

        required_string_fields = ("scene_id", "image_prompt", "video_prompt", "voice_prompt")
        for field in required_string_fields:
            value = output.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"Scene prompt output must include non-empty {field}.")
            elif self.contains_banned_testimonial(value):
                errors.append(f"{field} contains banned testimonial language.")

        safety_notes = output.get("safety_notes")
        if not isinstance(safety_notes, list) or not all(isinstance(note, str) for note in safety_notes):
            errors.append("Scene prompt output must include safety_notes as a list of strings.")

        return errors

    @staticmethod
    def _contains_cta(text: str) -> bool:
        normalized = (text or "").casefold()
        cta_phrases = ("link in bio", "use code", "shop now", "try for free", "limited time", "learn more")
        return any(phrase in normalized for phrase in cta_phrases)


def count_words(text: str) -> int:
    return ComplianceService.count_words(text)


def contains_banned_testimonial(text: str) -> bool:
    return ComplianceService.contains_banned_testimonial(text)


def validate_script(script: dict[str, Any], expected_scene_count: int) -> list[str]:
    return ComplianceService().validate_script(script, expected_scene_count)


def validate_scene_prompt_output(output: dict[str, Any]) -> list[str]:
    return ComplianceService().validate_scene_prompt_output(output)
