import shutil

from fastapi import APIRouter

from app.config import get_settings
from app.schemas import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    settings = get_settings()
    return HealthOut(
        status="ok",
        version=settings.version,
        ffmpeg=shutil.which("ffmpeg") is not None,
        yt_dlp=_has_yt_dlp(),
    )


def _has_yt_dlp() -> bool:
    try:
        import yt_dlp  # noqa: F401

        return True
    except ImportError:
        return False
