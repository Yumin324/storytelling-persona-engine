# UGCLABs

UGCLABs is a university final-year MVP for AI-assisted B-roll UGC ad production. It uses a real provider-backed pipeline to create scene-level production assets:

- first-frame image
- silent B-roll video clip
- voiceover audio clip
- scene metadata
- downloadable scene ZIP

The final edited advertisement is assembled manually in CapCut or another editor.

## Stack

- Frontend: React + Vite + Tailwind CSS
- Backend: FastAPI + Python
- Database: SQLite
- Storage: local filesystem
- Providers: OpenAI, Kling, ElevenLabs

## Environment

Create backend environment values from the example:

```bash
cp .env.example backend/.env
```

Fill in real provider credentials in `backend/.env`. Never commit `.env`.

Required keys are:

```env
APP_ENV=development
DATABASE_URL=sqlite:///./ugclabs.db
STORAGE_ROOT=./storage

OPENAI_API_KEY=
OPENAI_LLM_MODEL=gpt-5.2
OPENAI_IMAGE_MODEL=gpt-image-2

KLING_ACCESS_KEY=
KLING_SECRET_KEY=
KLING_API_BASE_URL=
KLING_VIDEO_MODEL=kling-v3

ELEVENLABS_API_KEY=
ELEVENLABS_DEFAULT_MODEL=eleven_v3

API_TIMEOUT_LLM_SECONDS=120
API_TIMEOUT_IMAGE_SECONDS=240
API_TIMEOUT_VIDEO_CREATE_SECONDS=120
API_TIMEOUT_VIDEO_POLL_TOTAL_SECONDS=1200
API_TIMEOUT_VOICE_SECONDS=120
API_RETRY_COUNT=3
PRODUCTION_SCENE_CONCURRENCY=2
```

The app shows a setup warning when provider keys are missing. `/api/health` also reports missing config and checks that `.env.example` contains the required variables.

Optional frontend override:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

The frontend defaults to `http://127.0.0.1:8000` when this is not set.

Do not commit real `.env` files, API keys, generated SQLite databases, provider outputs, logs, or build artifacts.

## Run App

After installing the backend and frontend dependencies once, run both servers from the repository root:

```bash
npm run dev
```

This starts:

```txt
Backend:  http://127.0.0.1:8000
Frontend: http://127.0.0.1:5173
```

## Backend Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend URL when running separately:

```txt
http://127.0.0.1:8000
```

Health check:

```bash
curl http://127.0.0.1:8000/api/health
```

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend URL when running separately:

```txt
http://127.0.0.1:5173
```

## Scripts

Repository root:

```bash
npm run dev
```

Frontend:

```bash
cd frontend
npm install
npm run dev
npm run build
npm run preview
```

Backend:

```bash
cd backend
python -m pytest tests
python -c "from app.main import app; print(app.title)"
```

There is currently no configured lint command or root-level build/test command.

## Demo Walkthrough

1. Open `Persona Bank`.
2. Click `Create Persona`.
3. Fill Identity, Physical Attributes, Voice, and Personality.
4. Click `Generate Influencer`.
5. Wait for the persona base image and character reference sheet to complete.
6. Open `Studio`.
7. Select the completed persona.
8. Configure outfit, accessories, environment, product details, scene count, and CTA.
9. Upload at least one product reference image.
10. Click `Generate References`.
11. Wait for session character, environment, and product reference sheets.
12. Click `Generate Script`.
13. Review or edit scene visual directions and voiceovers.
14. Continue to `Production`.
15. Click `Generate Ad`.
16. Watch scene cards update with prompts, first-frame image, video, and audio.
17. Download each completed scene ZIP.

## Backend Database And Storage

SQLite tables are created automatically on FastAPI startup. Generated files are stored under:

```txt
backend/storage/personas/
backend/storage/sessions/
backend/storage/jobs/
backend/storage/uploads/
```

Storage helpers use deterministic paths and prevent arbitrary client-controlled filesystem access. Generated storage assets are ignored by Git.

## Troubleshooting

### Missing API Key

The UI setup banner and provider error panels identify missing variables such as `OPENAI_API_KEY`, `KLING_API_KEY`, `KLING_API_BASE_URL`, or `ELEVENLABS_API_KEY`.

Fix: add the missing value to `backend/.env`, then restart FastAPI.

### OpenAI Timeout

Image generation can take several minutes. The backend timeout is controlled by `API_TIMEOUT_IMAGE_SECONDS`.

Fix: retry the failed persona, reference, script, or scene step. If repeated timeouts occur, increase the timeout value or reduce prompt/reference complexity.

### Kling Polling Timeout

Kling video generation creates a task and polls until completion. Polling stops at `API_TIMEOUT_VIDEO_POLL_TOTAL_SECONDS`.

Fix: retry the failed scene. If the provider is slow, increase the poll total timeout.

### ElevenLabs Voice Error

Voice listing or text-to-speech fails if the API key, voice ID, or model is invalid.

Fix: confirm `ELEVENLABS_API_KEY`, use `/api/voices` to verify available voices, and regenerate the persona voice selection if needed.

### Uploaded File Issue

Product uploads accept PNG, JPG, and WEBP only, with an 8 MB limit per file.

Fix: convert or resize the product image and upload again.

## Smoke Tests

Backend import:

```bash
cd backend
python -c "from app.main import app; print(app.title)"
```

Backend tests:

```bash
cd backend
python -m pytest tests
```

Frontend build:

```bash
cd frontend
npm run build
```

Git hygiene:

```bash
git status --short
git check-ignore backend/storage/jobs/1/scene_01/video.mp4
```

Secret scan:

```bash
rg --hidden --glob '!backend/.env' --glob '!**/.git/**' "OPENAI_API_KEY=\S|KLING_API_KEY=\S|KLING_ACCESS_KEY=\S|KLING_SECRET_KEY=\S|ELEVENLABS_API_KEY=\S"
rg --hidden --glob '!backend/.env' --glob '!**/.git/**' --glob '!frontend/package-lock.json' "sk-[A-Za-z0-9_-]{20,}"
rg --hidden --glob '!backend/.env' --glob '!**/.git/**' -- "-----BEGIN [A-Z ]*PRIVATE KEY-----"
```
