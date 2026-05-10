import json
import re
from pathlib import Path
from typing import Any


PLACEHOLDER_PATTERN = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s*}}")


class PromptRenderer:
    def __init__(self, prompt_dir: Path | None = None) -> None:
        self.prompt_dir = prompt_dir or Path(__file__).resolve().parents[1] / "prompts"

    def render_template(self, template_name: str, context: dict[str, Any]) -> str:
        template_text = self._load_template(template_name)

        def replace(match: re.Match[str]) -> str:
            key_path = match.group(1)
            value = self._resolve_context_value(key_path, context)
            if value is None:
                raise ValueError(f"Missing prompt context value: {key_path}")
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False)
            return str(value)

        rendered = PLACEHOLDER_PATTERN.sub(replace, template_text)
        unresolved = PLACEHOLDER_PATTERN.findall(rendered)
        if unresolved:
            raise ValueError(f"Unresolved prompt placeholders: {', '.join(sorted(set(unresolved)))}")
        return rendered

    def _load_template(self, template_name: str) -> str:
        path = self._safe_template_path(template_name)
        if path.suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            prompt = data.get("prompt")
            if not isinstance(prompt, str) or not prompt.strip():
                raise ValueError(f"Prompt JSON file {template_name} must include a non-empty prompt field.")
            return prompt
        return path.read_text(encoding="utf-8")

    def _safe_template_path(self, template_name: str) -> Path:
        if Path(template_name).name != template_name:
            raise ValueError("template_name must be a filename, not a path")
        path = (self.prompt_dir / template_name).resolve()
        prompt_root = self.prompt_dir.resolve()
        if path.parent != prompt_root:
            raise ValueError("template path escapes prompt directory")
        if not path.exists():
            raise FileNotFoundError(f"Prompt template not found: {template_name}")
        return path

    @staticmethod
    def _resolve_context_value(key_path: str, context: dict[str, Any]) -> Any:
        current: Any = context
        for part in key_path.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                raise ValueError(f"Missing prompt context value: {key_path}")
        return current
