from fastapi import Request

from app.config import Settings, get_settings
from app.core.database import Database


def get_db(request: Request) -> Database:
    return request.app.state.db


def get_app_settings() -> Settings:
    return get_settings()
