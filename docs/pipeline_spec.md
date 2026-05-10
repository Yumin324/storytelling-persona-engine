# pipeline_spec.md — UGCLABs Generation Pipeline

## Pipeline Overview

UGCLABs has three generation pipelines:

1. Persona generation pipeline
2. Studio/session generation pipeline
3. Production generation pipeline

All long-running pipelines must be job-based.

## Pipeline 1 — Persona Generation

### Trigger

User completes Persona Bank form and clicks `Generate Influencer`.

### Inputs

- name
- age
- gender
- physical attributes
- voice selection
- personality attributes

### Steps

#### Step 1 — Validate Persona

Validate:

- name is not empty
- age is 18–70
- gender is valid
- physical attributes complete
- voice selected
- personality attributes complete
- values count <= 2

#### Step 2 — Create Persona Record

Create persona with status:

```txt
queued
```

#### Step 3 — Generate Base Avatar

Use GPT Image 2.0 with `character_base.json`.

Prompt renderer must inject all persona attributes into the template.

Output:

```txt
storage/personas/{persona_id}/base.png
```

#### Step 4 — Generate Character Reference Sheet

Use GPT Image 2.0 with:

- base avatar image as input reference
- `character_reference.json` prompt

Output:

```txt
storage/personas/{persona_id}/reference_sheet.png
```

#### Step 5 — Finalize Persona

Update persona:

```txt
status = completed
base_image_path = ...
reference_sheet_path = ...
```

### Failure Behavior

If any step fails:

- set persona status to failed
- save error_message
- show retry generation button in UI

## Pipeline 2 — Studio Session Generation

### Trigger

User selects persona, fills Studio form, uploads product images, and clicks `Generate Script`.

This action performs two things:

1. Generate session reference assets.
2. Generate script.

Because reference asset generation can be slow, it must be job-based.

### Inputs

- persona ID
- outfit
- accessories
- environment selections
- product images
- product name
- product category
- key benefits
- target audience
- scene count
- CTA

### Steps

#### Step 1 — Validate Session Input

Validate:

- persona exists
- persona has completed reference sheet
- product name is present
- key benefits are present
- target audience is present
- scene count >= 3 and <= 10
- at least one product image uploaded
- CTA selected or custom CTA provided

#### Step 2 — Create / Update Session

Persist ad session fields.

#### Step 3 — Generate Session Character Reference

Use GPT Image 2.0 with:

- persona character reference sheet as input
- `session_character_edit.json` prompt
- outfit/accessory fields

Output:

```txt
storage/sessions/{session_id}/session_character_reference.png
```

Hard rule:

Only outfit and accessories may change. Identity must remain unchanged.

#### Step 4 — Generate Environment Base Image

Use GPT Image 2.0 with `environment_base.json`.

Output:

```txt
storage/sessions/{session_id}/environment_base.png
```

#### Step 5 — Generate Environment Reference Sheet

Use GPT Image 2.0 with:

- environment base image
- `environment_reference.json`

Output:

```txt
storage/sessions/{session_id}/environment_reference.png
```

#### Step 6 — Generate Product Reference Sheet

Use GPT Image 2.0 with:

- uploaded product images
- `product_reference.json`

Output:

```txt
storage/sessions/{session_id}/product_reference.png
```

#### Step 7 — Generate Script

Use GPT 5.2 with `script_writer.md`.

Inputs:

- persona personality
- product details
- key benefits
- target audience
- scene count
- CTA

Output must be valid structured JSON:

```json
{
  "persona_summary": "string",
  "scenes": [
    {
      "scene_id": "Scene 01",
      "visual": "string",
      "voiceover": "string"
    }
  ]
}
```

#### Step 8 — Compliance Audit

Before saving, backend must validate:

- scene count matches requested count
- every scene has visual and voiceover
- each voiceover <= 16 words
- target voiceover length should be 12–15 words where possible
- no first-person testimonial patterns
- no banned phrases
- CTA appears only once at the end

If validation fails, ask GPT 5.2 to repair the script once. If still invalid, return error.

## Pipeline 3 — Production Generation

### Trigger

User clicks `Generate Ad` in Production tab.

### Inputs

- completed session
- edited script
- session character reference sheet
- environment reference sheet
- product reference sheet
- persona voice config

### Steps

#### Step 1 — Create Production Job

Create job:

```txt
status = queued
progress_percent = 0
```

Return job ID immediately.

#### Step 2 — Convert Script to Scene Production Prompts

For each scene, call GPT 5.2 using `scene_prompt_writer.md`.

Input:

- scene ID
- visual
- voiceover
- persona identity summary
- persona personality
- environment summary
- product summary
- whether product is revealed in this scene

Output must be strict JSON:

```json
{
  "scene_id": "Scene 01",
  "image_prompt": "...",
  "video_prompt": "...",
  "voice_prompt": "...",
  "safety_notes": ["..."]
}
```

Save prompts to `scenes` table.

#### Step 3 — Generate Scene First Frame

For each scene:

Use GPT Image 2.0 with:

- scene image_prompt
- session character reference sheet
- environment reference sheet
- product reference sheet only during and after product reveal scene

Output:

```txt
storage/jobs/{job_id}/scene_XX/first_frame.png
```

#### Step 4 — Generate Silent Video Clip

Use Kling 3.0 with:

- first-frame image
- video_prompt
- duration: 8 seconds
- no audio
- natural UGC movement
- no cinematic motion
- no fast sudden movement

Output:

```txt
storage/jobs/{job_id}/scene_XX/video.mp4
```

Kling task behavior:

1. create task
2. store provider task ID
3. poll task
4. download completed video
5. save local video path

#### Step 5 — Generate Voiceover

Use ElevenLabs with:

- selected persona voice ID
- original voiceover text
- generated voice_prompt expression guidance

Output:

```txt
storage/jobs/{job_id}/scene_XX/voiceover.mp3
```

#### Step 6 — Create Scene Zip

Create zip containing:

```txt
scene_metadata.json
first_frame.png
video.mp4
voiceover.mp3
```

Output:

```txt
storage/jobs/{job_id}/scene_XX/scene_XX_assets.zip
```

#### Step 7 — Update Progress

Progress should update after every completed scene asset.

Recommended progress formula:

```txt
total_units = number_of_scenes × 3
completed_units = completed first frames + completed videos + completed voiceovers
progress_percent = completed_units / total_units × 100
```

#### Step 8 — Finalize Job

If every scene completed:

```txt
job.status = completed
```

If one or more scenes failed:

```txt
job.status = failed
```

But successful scene assets must remain accessible.

## Retry Behavior

User can retry a failed scene.

Retry should resume from the failed asset.

Examples:

- If image failed, regenerate image, video, voice, zip.
- If video failed, keep image and regenerate video, voice if needed, zip.
- If voice failed, keep image and video, regenerate voice and zip.

## Banned Script Patterns

Reject or repair scripts containing:

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
guaranteed
miracle
before I found
I struggled with
I was suffering
```

## Production Aesthetic Rules

All scene prompts must enforce:

- UGC B-roll
- phone-shot realism
- natural imperfections
- non-cinematic lighting
- no gimbal-like smoothness
- no commercial polish
- no dramatic film language
- no testimonial implication
- no direct talking-head scenes unless explicitly required
- slow natural camera movement
- stable product visibility during product reveal
