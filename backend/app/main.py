from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import files, health, personas, production, sessions, voices
from app.services.storage_service import StorageService


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    StorageService().ensure_base_directories()
    yield

app = FastAPI(
    title="UGCLABs API",
    description="Backend foundation for AI-generated B-roll UGC production assets.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(voices.router, prefix="/api", tags=["voices"])
app.include_router(personas.router, prefix="/api", tags=["personas"])
app.include_router(sessions.router, prefix="/api", tags=["sessions"])
app.include_router(production.router, prefix="/api", tags=["production"])
app.include_router(files.router, prefix="/api", tags=["files"])
