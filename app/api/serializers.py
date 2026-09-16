from app.config import Settings


def _base(value: str) -> str:
    return value.rstrip("/")


def resolve_base_url(request_base: str, settings: Settings) -> str:
    if settings.public_base_url:
        return _base(settings.public_base_url)
    return _base(request_base)


def pair_url_for(base: str, code: str) -> str:
    return f"{base}/s/{code}"


def media_http_url(base: str, session_id: str, filename: str) -> str:
    return f"{base}/media/{session_id}/{filename}"


def media_stream_path(
    settings: Settings, session_id: str, filename: str
) -> str | None:
    if not settings.smb_prefix:
        return None
    return f"{settings.smb_prefix.rstrip('/')}/{session_id}/{filename}"


def serialize_item(item: dict | None, settings: Settings, base: str) -> dict | None:
    if item is None:
        return None
    filename = item.get("filename")
    http_url = stream_path = None
    if filename:
        http_url = media_http_url(base, item["session_id"], filename)
        stream_path = media_stream_path(settings, item["session_id"], filename)
    return {
        "id": item["id"],
        "position": item["position"],
        "url": item["url"],
        "title": item.get("title"),
        "status": item["status"],
        "progress": item.get("progress", 0.0),
        "duration": item.get("duration"),
        "error": item.get("error"),
        "stream_path": stream_path,
        "http_url": http_url,
        "created_at": item["created_at"],
        "updated_at": item["updated_at"],
    }


def serialize_session(
    session: dict, current: dict | None, settings: Settings, base: str
) -> dict:
    return {
        "id": session["id"],
        "code": session["code"],
        "status": "playing" if current else "idle",
        "pair_url": pair_url_for(base, session["code"]),
        "qr_url": f"{base}/api/v1/sessions/{session['id']}/qr.png",
        "current_item": serialize_item(current, settings, base),
        "created_at": session["created_at"],
    }
