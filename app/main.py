from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import health, media, sessions
from app.config import get_settings
from app.core.database import Database
from app.services.worker import QueueWorker

WEB_DIR = Path(__file__).parent / "web"
SETTINGS = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    settings.temp_dir.mkdir(parents=True, exist_ok=True)

    app.state.settings = settings
    app.state.db = Database(settings.db_path)
    app.state.worker = QueueWorker(app.state.db, settings)

    if settings.worker_enabled:
        app.state.worker.start()
    try:
        yield
    finally:
        await app.state.worker.stop()


app = FastAPI(
    title=SETTINGS.app_name,
    version=SETTINGS.version,
    description="Backend de PS2Tube: cola de YouTube y conversion a MPEG-PS para PS2.",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(media.router)
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse("/docs")


@app.get("/s/{code}", include_in_schema=False)
def mobile(code: str) -> FileResponse:
    return FileResponse(WEB_DIR / "static" / "index.html")
