# architecture.md — UGCLABs Technical Architecture

## Architectural Philosophy

UGCLABs is a long-running AI generation app. The main technical risk is slow external API calls. Therefore, the architecture must separate user requests from generation execution.

The frontend must never wait for the full persona/session/ad generation pipeline in one HTTP request.

## System Overview

```txt
React Frontend
    ↓ HTTP
FastAPI Backend
    ↓
SQLite Database
    ↓
Local Storage
    ↓
Provider Clients
    ├── OpenAI LLM: GPT 5.2
    ├── OpenAI Image: GPT Image 2.0
    ├── Kling Video: Kling 3.0
    └── ElevenLabs Voice
```

## Backend Directory Structure

```txt
backend/
  app/
    main.py
    config.py
    database.py
    models.py
    schemas.py
    errors.py

    routers/
      health.py
      personas.py
      sessions.py
      production.py
      files.py
      voices.py

    services/
      storage_service.py
      prompt_renderer.py
      compliance_service.py
      provider_base.py
      openai_llm_service.py
      openai_image_service.py
      kling_video_service.py
      elevenlabs_voice_service.py
      pipeline_service.py
      zip_service.py

    workers/
      task_registry.py
      job_runner.py

    prompts/
      character_base.json
      character_reference.json
      session_character_edit.json
      environment_base.json
      environment_reference.json
      product_reference.json
      script_writer.md
      scene_prompt_writer.md

  storage/
    personas/
    sessions/
    jobs/
    uploads/
```

## Frontend Directory Structure

```txt
frontend/
  src/
    main.jsx
    App.jsx
    api/
      client.js
      personas.js
      sessions.js
      production.js
      files.js
      voices.js
    components/
      Layout.jsx
      TopNav.jsx
      StatusBadge.jsx
      FilePreview.jsx
      ErrorPanel.jsx
      ProgressBar.jsx
    pages/
      PersonaBank.jsx
      Studio.jsx
      Production.jsx
    features/
      persona/
        PersonaForm.jsx
        PersonaCard.jsx
      studio/
        InfluencerPicker.jsx
        SessionCustomizationForm.jsx
        EnvironmentForm.jsx
        ProductForm.jsx
        ScriptEditor.jsx
      production/
        ProductionSummary.jsx
        SceneCard.jsx
        JobProgress.jsx
    styles/
      index.css
```

## Database Tables

### personas

Stores permanent influencer/persona profiles.

Fields:

- id
- name
- age
- gender
- physical_json
- voice_json
- personality_json
- base_image_path
- reference_sheet_path
- status
- error_message
- created_at
- updated_at

### ad_sessions

Stores one ad concept/session.

Fields:

- id
- persona_id
- outfit
- accessories_json
- environment_json
- product_json
- product_upload_paths_json
- script_json
- session_character_ref_path
- environment_base_path
- environment_ref_path
- product_ref_path
- status
- error_message
- created_at
- updated_at

### production_jobs

Tracks full ad generation jobs.

Fields:

- id
- session_id
- status
- progress_percent
- current_step
- error_message
- started_at
- completed_at
- created_at
- updated_at

### scenes

Tracks each production scene.

Fields:

- id
- session_id
- job_id
- scene_number
- script_visual
- script_voiceover
- image_prompt
- video_prompt
- voice_prompt
- first_frame_path
- video_path
- voice_path
- zip_path
- status
- error_message
- created_at
- updated_at

### api_logs

Stores provider call logs for debugging.

Fields:

- id
- provider
- operation
- related_type
- related_id
- request_summary_json
- response_summary_json
- status
- status_code
- duration_ms
- error_message
- created_at

Never store full API keys, secrets, or private headers.

## API Design

### Health

```txt
GET /api/health
```

Returns backend status and configuration readiness without exposing secrets.

### Personas

```txt
GET    /api/personas
POST   /api/personas
GET    /api/personas/{persona_id}
DELETE /api/personas/{persona_id}
POST   /api/personas/{persona_id}/generate-assets
GET    /api/personas/jobs/{job_id}
```

Persona asset generation must be asynchronous.

### Voices

```txt
GET /api/voices
```

Fetches ElevenLabs voices and returns normalized voice objects.

### Sessions

```txt
POST /api/sessions
GET  /api/sessions/{session_id}
PUT  /api/sessions/{session_id}
POST /api/sessions/{session_id}/generate-references
GET  /api/sessions/{session_id}/reference-job/{job_id}
POST /api/sessions/{session_id}/generate-script
PUT  /api/sessions/{session_id}/script
```

Session reference generation must be asynchronous.

Script generation may be a regular request if fast, but still must use timeout and error handling.

### Production

```txt
POST /api/production/{session_id}/start
GET  /api/production/jobs/{job_id}
GET  /api/production/jobs/{job_id}/scenes
POST /api/production/scenes/{scene_id}/retry
GET  /api/production/scenes/{scene_id}/download
```

## Job System

A simple in-process job runner is acceptable for the university MVP.

Required behavior:

- Create job row first.
- Return job ID immediately.
- Run job in background.
- Update database after each step.
- Frontend polls job endpoint.
- Failed steps record structured errors.
- User can retry failed scene.

Use FastAPI BackgroundTasks or an asyncio task registry.

## Provider Client Design

Every provider service must expose clear methods.

### OpenAI LLM Service

```python
class OpenAILLMService:
    async def generate_script(self, payload: ScriptInput) -> ScriptOutput: ...
    async def generate_scene_prompts(self, payload: ScenePromptInput) -> ScenePromptOutput: ...
```

### OpenAI Image Service

```python
class OpenAIImageService:
    async def generate_image(self, prompt: str, input_images: list[str] | None, output_path: str) -> str: ...
```

### Kling Video Service

```python
class KlingVideoService:
    async def create_video_task(self, image_path: str, prompt: str) -> str: ...
    async def poll_video_task(self, task_id: str, output_path: str) -> str: ...
```

### ElevenLabs Voice Service

```python
class ElevenLabsVoiceService:
    async def text_to_speech(self, voice_id: str, text: str, voice_prompt: str, output_path: str) -> str: ...
```

## Timeout and Retry Policy

### LLM

- Timeout: 120 seconds
- Retries: 3
- Backoff: 2s, 5s, 10s

### Image

- Timeout: 240 seconds
- Retries: 3
- Backoff: 5s, 15s, 30s

### Video

- Create task timeout: 120 seconds
- Poll total timeout: 1200 seconds
- Poll interval: 10 seconds
- Retries for create task: 3
- Polling must stop clearly if timeout is reached

### Voice

- Timeout: 120 seconds
- Retries: 3
- Backoff: 2s, 5s, 10s

## Error Handling

Normalize provider errors into this shape:

```json
{
  "provider": "openai|kling|elevenlabs",
  "operation": "string",
  "status": "failed",
  "message": "human-readable message",
  "retryable": true,
  "raw_error_summary": "safe shortened error"
}
```

UI must show useful messages:

- Missing API key
- Rate limited
- Timeout
- Invalid provider response
- File save failed
- Prompt validation failed

## Storage Paths

Use deterministic local paths:

```txt
storage/personas/{persona_id}/base.png
storage/personas/{persona_id}/reference_sheet.png

storage/sessions/{session_id}/session_character_reference.png
storage/sessions/{session_id}/environment_base.png
storage/sessions/{session_id}/environment_reference.png
storage/sessions/{session_id}/product_reference.png
storage/sessions/{session_id}/uploads/product_001.png

storage/jobs/{job_id}/scene_01/first_frame.png
storage/jobs/{job_id}/scene_01/video.mp4
storage/jobs/{job_id}/scene_01/voiceover.mp3
storage/jobs/{job_id}/scene_01/scene_01_assets.zip
```

## Frontend Polling

Frontend should poll:

- every 2 seconds for jobs
- every 5 seconds after 5 minutes
- stop polling when job reaches completed, failed, or cancelled

## Security Notes

- Never expose API keys to frontend.
- All provider calls happen backend-side.
- Validate uploaded image types.
- Limit upload size.
- Do not allow arbitrary file paths from client input.

## Commit Standard

Every implementation stage must end with:

```bash
git status
git add .
git commit -m "<type>: <meaningful summary>"
```
