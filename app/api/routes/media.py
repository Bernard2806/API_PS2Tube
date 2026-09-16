from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api.deps import get_app_settings
from app.config import Settings

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/{session_id}/{filename}")
def get_media(
    session_id: str,
    filename: str,
    settings: Settings = Depends(get_app_settings),
) -> FileResponse:
    media_root = settings.media_dir.resolve()
    target = (media_root / session_id / filename).resolve()

    if not target.is_relative_to(media_root) or not target.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    return FileResponse(target, media_type="video/mpeg", filename=filename)
