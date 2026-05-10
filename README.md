# UGCLABs

UGCLABs is a university final-year MVP for AI-assisted B-roll UGC ad production. The app is structured as a real provider-backed pipeline: FastAPI handles configuration, provider calls, jobs, storage, and future SQLite persistence; React + Vite + Tailwind CSS provides the Persona Bank, Studio, and Production workspace.

This initial stage only creates a clean, runnable foundation. It does not implement persona generation, session generation, or production jobs yet.

## Stack

- Frontend: React + Vite + Tailwind CSS
- Backend: FastAPI + Python
- Database: SQLite
- Storage: local filesystem
- Providers: OpenAI, Kling, ElevenLabs

## Setup

Create backend environment values from the example:

```bash
cp .env.example backend/.env
```

Fill in real provider credentials in `backend/.env`. Missing keys are reported by `/api/health`; they are never treated as successful generation readiness.

## Backend Database And Storage

The backend uses SQLite through SQLAlchemy. On FastAPI startup it creates the required tables for:

- `personas`
- `ad_sessions`
- `production_jobs`
- `scenes`
- `api_logs`

The startup hook also creates the local storage roots:

```txt
backend/storage/personas/
backend/storage/sessions/
backend/storage/jobs/
backend/storage/uploads/
```

Generated assets will use deterministic paths such as `storage/personas/{persona_id}/`, `storage/sessions/{session_id}/`, and `storage/jobs/{job_id}/scene_XX/`. Storage helpers validate IDs and filenames so client-provided arbitrary paths cannot escape the configured storage root.

## Run Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend health check:

```bash
curl http://127.0.0.1:8000/api/health
```

## Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend dev server:

```bash
http://127.0.0.1:5173
```

## Build Checks

Backend import check:

```bash
cd backend
python -c "from app.main import app; print(app.title)"
```

Frontend production build:

```bash
cd frontend
npm run build
```
