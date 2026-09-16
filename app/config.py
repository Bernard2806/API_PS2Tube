from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="PS2TUBE_", extra="ignore"
    )

    app_name: str = "PS2Tube API"
    version: str = "0.1.0"
    host: str = "0.0.0.0"
    port: int = 8000

    public_base_url: str | None = None

    data_dir: Path = Path("data")
    default_profile: str = "mpeg2"
    max_height: int = 480
    prefetch_ahead: int = 1
    code_length: int = 6
    worker_interval: float = 2.0
    worker_enabled: bool = True
    keep_temp: bool = False

    smb_prefix: str | None = None

    @property
    def media_dir(self) -> Path:
        return self.data_dir / "media"

    @property
    def temp_dir(self) -> Path:
        return self.data_dir / "tmp"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "ps2tube.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
