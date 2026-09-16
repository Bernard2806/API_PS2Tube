import io

import segno
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.deps import get_app_settings, get_db
from app.api.serializers import (
    pair_url_for,
    resolve_base_url,
    serialize_item,
    serialize_session,
)
from app.config import Settings
from app.core.database import Database
from app.core.ids import new_code
from app.schemas import (
    NextItemOut,
    QueueAddRequest,
    QueueItemOut,
    ReorderRequest,
    SessionOut,
)

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


def _session_or_404(db: Database, session_id: str) -> dict:
    session = db.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sesion no encontrada")
    return session


def _current(db: Database, session: dict) -> dict | None:
    if session["current_item_id"]:
        return db.get_item(session["current_item_id"])
    return None


def _resolve_current(db: Database, session: dict) -> dict | None:
    current = _current(db, session)
    if current is not None:
        return current
    items = db.get_items(session["id"])
    upcoming = next(
        (i for i in items if i["status"] not in ("done", "failed")), None
    )
    if upcoming is not None:
        db.set_current_item(session["id"], upcoming["id"])
    return upcoming


def _unique_code(db: Database, length: int) -> str:
    for _ in range(20):
        code = new_code(length)
        if db.get_session_by_code(code) is None:
            return code
    raise HTTPException(status_code=500, detail="No se pudo generar un codigo")


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(
    request: Request,
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict:
    session = db.create_session(_unique_code(db, settings.code_length))
    base = resolve_base_url(str(request.base_url), settings)
    return serialize_session(session, None, settings, base)


@router.get("/code/{code}", response_model=SessionOut)
def get_session_by_code(
    code: str,
    request: Request,
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict:
    session = db.get_session_by_code(code)
    if session is None:
        raise HTTPException(status_code=404, detail="Codigo invalido")
    base = resolve_base_url(str(request.base_url), settings)
    return serialize_session(session, _current(db, session), settings, base)


@router.get("/{session_id}", response_model=SessionOut)
def get_session(
    session_id: str,
    request: Request,
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict:
    session = _session_or_404(db, session_id)
    base = resolve_base_url(str(request.base_url), settings)
    return serialize_session(session, _current(db, session), settings, base)


@router.get("/{session_id}/queue", response_model=list[QueueItemOut])
def list_queue(
    session_id: str,
    request: Request,
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> list[dict]:
    _session_or_404(db, session_id)
    base = resolve_base_url(str(request.base_url), settings)
    return [serialize_item(i, settings, base) for i in db.get_items(session_id)]


@router.post(
    "/{session_id}/queue",
    response_model=list[QueueItemOut],
    status_code=status.HTTP_201_CREATED,
)
def add_to_queue(
    session_id: str,
    payload: QueueAddRequest,
    request: Request,
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> list[dict]:
    _session_or_404(db, session_id)
    base = resolve_base_url(str(request.base_url), settings)
    created = [db.add_item(session_id, url) for url in payload.urls]
    return [serialize_item(i, settings, base) for i in created]


@router.post("/{session_id}/queue/reorder", response_model=list[QueueItemOut])
def reorder_queue(
    session_id: str,
    payload: ReorderRequest,
    request: Request,
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> list[dict]:
    _session_or_404(db, session_id)
    db.reorder_items(session_id, payload.item_ids)
    base = resolve_base_url(str(request.base_url), settings)
    return [serialize_item(i, settings, base) for i in db.get_items(session_id)]


@router.delete(
    "/{session_id}/queue/{item_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_item(
    session_id: str,
    item_id: str,
    db: Database = Depends(get_db),
) -> Response:
    _session_or_404(db, session_id)
    if not db.delete_item(session_id, item_id):
        raise HTTPException(status_code=404, detail="Item no encontrado")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{session_id}/queue/{item_id}/play", response_model=SessionOut)
def play_now(
    session_id: str,
    item_id: str,
    request: Request,
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict:
    _session_or_404(db, session_id)
    item = db.get_item(item_id)
    if item is None or item["session_id"] != session_id:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    db.set_current_item(session_id, item_id)
    session = db.get_session(session_id)
    base = resolve_base_url(str(request.base_url), settings)
    return serialize_session(session, item, settings, base)


@router.post("/{session_id}/complete", response_model=SessionOut)
def complete_current(
    session_id: str,
    request: Request,
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict:
    _session_or_404(db, session_id)
    db.complete_current(session_id)
    session = db.get_session(session_id)
    base = resolve_base_url(str(request.base_url), settings)
    return serialize_session(session, _current(db, session), settings, base)


@router.get(
    "/{session_id}/next",
    response_model=NextItemOut,
    responses={204: {"description": "Todavia no hay un video listo"}},
)
def next_item(
    session_id: str,
    request: Request,
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    session = _session_or_404(db, session_id)
    base = resolve_base_url(str(request.base_url), settings)

    current = _resolve_current(db, session)
    while current is not None and current["status"] == "failed":
        session = db.complete_current(session_id)
        current = _resolve_current(db, session)

    if current is None or current["status"] != "ready":
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    item = db.update_item(current["id"], status="playing")
    serialized = serialize_item(item, settings, base)
    return {
        "item": serialized,
        "stream_path": serialized["stream_path"],
        "http_url": serialized["http_url"],
    }


@router.get("/{session_id}/qr.png", include_in_schema=False)
def qr_png(
    session_id: str,
    request: Request,
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> Response:
    session = _session_or_404(db, session_id)
    base = resolve_base_url(str(request.base_url), settings)
    buffer = io.BytesIO()
    segno.make(pair_url_for(base, session["code"]), error="m").save(
        buffer, kind="png", scale=8, border=2
    )
    return Response(buffer.getvalue(), media_type="image/png")
