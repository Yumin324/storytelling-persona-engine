# AGENT.md — UGCLABs Codex Build Rules

## Project Identity

UGCLABs is a university final-year MVP for generating AI-assisted B-roll UGC ads using a structured production workflow.

The system allows a user to:

1. Create and store AI influencer/persona profiles.
2. Configure a UGC ad session around a persona, environment, outfit, accessories, and product.
3. Generate a compliant, non-testimonial ad script.
4. Generate scene-level production prompts.
5. Generate first-frame images, silent B-roll video clips, and voiceover clips.
6. Download each scene's assets for final editing in CapCut or another editor.

This project must be treated as a real production pipeline, not a toy demo.

## Required Technology Stack

Use exactly this stack unless the user explicitly changes it:

- Frontend: React + Vite + Tailwind CSS
- Backend: FastAPI + Python
- Database: SQLite
- Storage: local filesystem folders
- Image generation: GPT Image 2.0
- Video generation: Kling 3.0
- Voiceover generation: ElevenLabs
- LLM: GPT 5.2
- Version control: GitHub with meaningful commits after every completed stage

## Non-Negotiable Product Rules

1. No mock provider system.
2. No fake asset generation.
3. No fallback assets pretending to be real generated outputs.
4. All AI providers must be integrated as real provider services.
5. Missing API keys must produce clear setup errors, not silent success.
6. API failures must be displayed clearly in the UI.
7. Long AI calls must never block the frontend indefinitely.
8. All long AI operations must run through backend jobs with persistent status.
9. Every scene must be independently trackable, retryable, and downloadable.
10. The app must preserve all generated files locally.

## Critical Reliability Rule

External AI APIs can be slow, unstable, rate-limited, or temporarily unavailable. The solution is not to wait forever. The solution is:

- background jobs
- explicit timeout limits
- retry with exponential backoff
- polling for long-running provider tasks
- persistent job state in SQLite
- structured error messages
- resumable scene-level processing

Never implement a route where the browser waits for a full ad generation to complete in one request.

Correct pattern:

```txt
User clicks Generate Ad
→ backend creates production job
→ backend immediately returns job_id
→ frontend polls job status
→ backend processes steps asynchronously
→ UI updates scene cards as assets complete
```

## Development Priorities

Build in this order:

1. Repository structure and documentation.
2. Backend foundation.
3. Database schema.
4. Provider client wrappers.
5. Persona Bank.
6. Studio session flow.
7. Script generation.
8. Production prompt generation.
9. Production asset generation.
10. UI polish, testing, and final demo readiness.

Do not build authentication, billing, cloud deployment, teams, analytics, or advanced admin panels.

## Git Rules

At the end of each meaningful stage:

```bash
git status
git add .
git commit -m "meaningful message"
```

Commit messages must describe completed functionality, not vague progress.

Good examples:

```txt
chore: initialize UGCLABs project structure and documentation
feat: add FastAPI database models and migration setup
feat: implement Persona Bank creation workflow
feat: add async production job pipeline
```

Bad examples:

```txt
update
changes
final
fix stuff
```

## Coding Quality Rules

- Keep functions small and readable.
- Use typed Pydantic schemas on backend.
- Validate every user input.
- Keep frontend forms controlled and predictable.
- Use clear loading, running, success, failed, and retry states.
- Never swallow exceptions silently.
- Log provider request metadata without exposing API keys.
- Store generated files using deterministic paths.
- Avoid clever abstractions that slow completion.

## Required Environment Variables

Create `.env.example` with:

```env
APP_ENV=development
DATABASE_URL=sqlite:///./ugclabs.db
STORAGE_ROOT=./storage

OPENAI_API_KEY=
OPENAI_LLM_MODEL=gpt-5.2
OPENAI_IMAGE_MODEL=gpt-image-2

KLING_API_KEY=
KLING_API_BASE_URL=
KLING_VIDEO_MODEL=kling-3.0

ELEVENLABS_API_KEY=
ELEVENLABS_DEFAULT_MODEL=

API_TIMEOUT_LLM_SECONDS=120
API_TIMEOUT_IMAGE_SECONDS=240
API_TIMEOUT_VIDEO_CREATE_SECONDS=120
API_TIMEOUT_VIDEO_POLL_TOTAL_SECONDS=1200
API_TIMEOUT_VOICE_SECONDS=120
API_RETRY_COUNT=3
```

Never commit real `.env` files.

## Completion Standard

The project is considered complete when this demo path works:

1. User creates a persona.
2. Persona is saved with attributes, voice config, base image, and character reference sheet.
3. User selects persona in Studio.
4. User configures outfit, accessories, environment, product, benefits, scene count, and CTA.
5. System generates session references and compliant script.
6. User edits script.
7. User continues to Production.
8. User starts Generate Ad job.
9. UI shows job progress and scene cards.
10. Each scene produces first-frame image, silent video, and voiceover.
11. User downloads each scene as a zip.
