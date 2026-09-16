from datetime import datetime
from enum import Enum
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

ALLOWED_HOSTS = (
    "youtube.com",
    "youtu.be",
    "youtube-nocookie.com",
)


class ItemStatus(str, Enum):
    queued = "queued"
    converting = "converting"
    ready = "ready"
    playing = "playing"
    done = "done"
    failed = "failed"


class SessionStatus(str, Enum):
    idle = "idle"
    playing = "playing"


def _validate_youtube_url(value: str) -> str:
    value = value.strip()
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("La URL debe empezar con http:// o https://")
    host = (parsed.hostname or "").lower()
    if not any(host == h or host.endswith(f".{h}") for h in ALLOWED_HOSTS):
        raise ValueError("Solo se admiten enlaces de YouTube")
    return value


class QueueItemCreate(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def check_url(cls, value: str) -> str:
        return _validate_youtube_url(value)


class QueueAddRequest(BaseModel):
    urls: list[str] = Field(min_length=1)

    @field_validator("urls")
    @classmethod
    def check_urls(cls, values: list[str]) -> list[str]:
        return [_validate_youtube_url(v) for v in values]


class ReorderRequest(BaseModel):
    item_ids: list[str] = Field(min_length=1)


class QueueItemOut(BaseModel):
    id: str
    position: int
    url: str
    title: str | None = None
    status: ItemStatus
    progress: float = 0.0
    duration: float | None = None
    error: str | None = None
    stream_path: str | None = None
    http_url: str | None = None
    created_at: datetime
    updated_at: datetime


class SessionOut(BaseModel):
    id: str
    code: str
    status: SessionStatus
    pair_url: str
    qr_url: str
    current_item: QueueItemOut | None = None
    created_at: datetime


class NextItemOut(BaseModel):
    item: QueueItemOut
    stream_path: str | None = None
    http_url: str | None = None


class HealthOut(BaseModel):
    status: str
    version: str
    ffmpeg: bool
    yt_dlp: bool
