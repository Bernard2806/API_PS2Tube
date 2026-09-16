import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PS2TUBE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PS2TUBE_WORKER_ENABLED", "false")

    from app.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()
