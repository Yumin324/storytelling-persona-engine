# prompt_templates.md — UGCLABs Prompt Integration Specification

## Purpose

This file tells Codex how to integrate all prompt templates into the application.

The user has provided detailed source prompt templates for:

1. Character base generation
2. Character reference sheet generation
3. Session outfit/accessory character reference edit
4. Environment base generation
5. Environment reference sheet generation
6. Product reference sheet generation
7. Script writer system prompt
8. Scene breakdown and production prompt writer system prompt

Codex must preserve the creative intent and constraints of those templates while converting them into maintainable backend prompt files.

## Prompt File Locations

Create these files:

```txt
backend/app/prompts/character_base.json
backend/app/prompts/character_reference.json
backend/app/prompts/session_character_edit.json
backend/app/prompts/environment_base.json
backend/app/prompts/environment_reference.json
backend/app/prompts/product_reference.json
backend/app/prompts/script_writer.md
backend/app/prompts/scene_prompt_writer.md
```

## Prompt Rendering Rules

Use a small prompt rendering service:

```python
class PromptRenderer:
    def render_template(self, template_name: str, context: dict) -> str:
        ...
```

Requirements:

- Use Jinja2 or a simple safe replacement system.
- Do not hardcode example values from the project brief.
- Replace all examples such as `swetha`, `19`, `female`, `Bedroom`, `luxury`, etc. with dynamic values.
- Validate that no unresolved `{{ placeholder }}` remains before making an API call.
- Save the final rendered prompt into database logs or scene metadata for debugging.

## Global Placeholder Conventions

Use these placeholder namespaces:

```txt
persona.*
session.*
environment.*
product.*
script.*
scene.*
meta.*
```

Examples:

```txt
{{ persona.id }}
{{ persona.name }}
{{ persona.age }}
{{ persona.gender }}
{{ persona.physical.ethnicity }}
{{ persona.physical.skin_tone }}
{{ persona.physical.face_shape }}
{{ persona.voice.voice_id }}
{{ persona.personality.core_personality }}
{{ session.outfit }}
{{ session.accessories }}
{{ environment.primary_environment }}
{{ product.name }}
{{ product.key_benefits }}
{{ scene.scene_id }}
{{ scene.visual }}
{{ scene.voiceover }}
{{ meta.timestamp }}
```

## Template 1 — Character Base Generation

File:

```txt
backend/app/prompts/character_base.json
```

Model:

```txt
GPT Image 2.0
```

Purpose:

Generate a high-fidelity hyper-realistic base avatar portrait from persona physical attributes.

Required dynamic inputs:

- persona.name
- persona.age
- persona.gender
- persona.physical.ethnicity
- persona.physical.skin_tone
- persona.physical.face_shape
- persona.physical.jawline
- persona.physical.cheekbones
- persona.physical.eye_shape
- persona.physical.eye_color
- persona.physical.eyebrow_shape
- persona.physical.eyebrow_color
- persona.physical.nose_shape
- persona.physical.mouth_shape
- persona.physical.lip_fullness
- persona.physical.hair_length
- persona.physical.hair_texture
- persona.physical.default_hair_color
- persona.physical.facial_hair
- persona.physical.body_type
- persona.physical.distinguishing_features

Core constraints to preserve:

- single hyper-realistic human individual
- waist-up portrait
- natural 3/4 angle
- no props
- no stylized filters
- true-to-life skin tones
- realistic pores, hair strands, lips, and eyes
- no airbrushing
- no cartoon/illustration
- no watermarks or text

## Template 2 — Character Reference Sheet

File:

```txt
backend/app/prompts/character_reference.json
```

Model:

```txt
GPT Image 2.0
```

Input image:

```txt
persona base avatar image
```

Purpose:

Generate identity-locked 3x3 character reference sheet.

Core constraints to preserve:

- absolute identity preservation
- facial geometry preservation
- skin texture preservation
- hair preservation
- pose variation accuracy
- 3x3 contact sheet
- zero beautification
- no face reshaping
- no skin smoothing
- no outfit alteration unless source outfit exists

## Template 3 — Session Character Edit

File:

```txt
backend/app/prompts/session_character_edit.json
```

Model:

```txt
GPT Image 2.0
```

Input image:

```txt
persona character reference sheet
```

Purpose:

Apply outfit and accessory changes for the current ad session without permanently modifying the persona.

Dynamic inputs:

- session.outfit
- session.accessories
- persona.gender

Core constraints:

- change only outfit/accessories
- preserve face, anatomy, skin tone, hair, body proportions, pose, lighting, and layout
- no identity drift
- no extra accessories unless selected
- output complete reference sheet

## Template 4 — Environment Base Generation

File:

```txt
backend/app/prompts/environment_base.json
```

Model:

```txt
GPT Image 2.0
```

Dynamic inputs:

- environment.primary_environment
- environment.time_of_day
- environment.lighting_style
- environment.aesthetic

Purpose:

Generate a high-fidelity environment image for the ad setting.

Core constraints:

- photorealistic
- physically accurate lighting
- correct perspective
- no warped geometry
- no AI smearing
- no characters unless distant implied scale is necessary
- environment must fit UGC ad context

## Template 5 — Environment Reference Sheet

File:

```txt
backend/app/prompts/environment_reference.json
```

Model:

```txt
GPT Image 2.0
```

Input image:

```txt
environment base image
```

Purpose:

Generate a 3x3 environment reference sheet from the same environment.

Core constraints:

- same environment across all panels
- no text, labels, watermarks, annotations, or UI
- consistent light source
- sealed color palette
- locked proportions
- clean 3x3 grid

## Template 6 — Product Reference Sheet

File:

```txt
backend/app/prompts/product_reference.json
```

Model:

```txt
GPT Image 2.0
```

Input images:

```txt
uploaded product images
```

Purpose:

Generate a 9-angle product reference sheet.

Core constraints:

- extract only details visible in source images
- no hallucinated product features
- consistent materials, colors, geometry
- multi-angle reference grid
- unverified surfaces should be flagged if necessary
- product consistency is more important than beauty

## Template 7 — Script Writer

File:

```txt
backend/app/prompts/script_writer.md
```

Model:

```txt
GPT 5.2
```

Purpose:

Generate a structured UGC B-roll ad script in the persona's style.

Input:

- persona name
- core personality
- content niche
- communication style
- humor level
- values
- product name
- product category
- key benefits
- target audience
- number of scenes
- CTA

Required output:

Strict JSON only:

```json
{
  "persona_summary": "Name — niche, communication style, humor level, values",
  "scenes": [
    {
      "scene_id": "Scene 01",
      "visual": "Precise UGC B-roll visual direction",
      "voiceover": "Short compliant voiceover"
    }
  ]
}
```

Must enforce:

- no personal testimonials
- no false claims
- no first-person experience
- no unverifiable claims
- product-focused framing
- Hook → Problem → Solution → Demo/Benefits → CTA
- voiceover <= 30 words, ideally 12–15 words
- exact scene count

## Template 8 — Scene Prompt Writer

File:

```txt
backend/app/prompts/scene_prompt_writer.md
```

Model:

```txt
GPT 5.2
```

Purpose:

Convert each approved script scene into production prompts for image, video, and voice.

Input:

- scene_id
- script visual
- script voiceover
- persona summary
- persona personality
- environment selection
- product summary
- product reveal status

Required output:

Strict JSON only:

```json
{
  "scene_id": "Scene 01",
  "image_prompt": "Prompt for GPT Image 2.0 first frame generation",
  "video_prompt": "Prompt for Kling 3.0 animation",
  "voice_prompt": "Prompt for ElevenLabs expression/prosody",
  "safety_notes": ["short notes about testimonial/claim compliance"]
}
```

Must enforce:

- phone-shot UGC B-roll
- iPhone 14 Pro or iPhone 15 Pro visual language
- no cinematic ad style
- no direct testimonial performance
- no fast sudden movement
- slow natural handheld movement
- no gimbal smoothness
- no impossible camera physics
- keep character, environment, and product consistent
- product reference sheet used only during and after product reveal

## Backend Compliance Validator

Prompt instructions are not enough. Add backend validation.

Create:

```txt
backend/app/services/compliance_service.py
```

Required checks:

```python
def count_words(text: str) -> int: ...
def contains_banned_testimonial(text: str) -> bool: ...
def validate_script(script: dict, expected_scene_count: int) -> list[str]: ...
def validate_scene_prompt_output(output: dict) -> list[str]: ...
```

Banned phrases include:

```txt
I tried
I've tried
I used
I've used
I started using
my results
my skin was
my hair was
changed my life
saved me
cured
miracle
guaranteed
before I found
I struggled with
I was suffering
```

## Important Implementation Note

The prompt templates from the project brief are long. Codex must copy their full content into the prompt files, then replace example values with dynamic placeholders. Do not shorten the source prompts in the actual app unless necessary for provider token limits.
