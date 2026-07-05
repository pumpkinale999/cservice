"""Application settings (CSERVICE_*)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    cservice_db_path: Path = Path("./data/cservice.db")
    cservice_data_root: Path = Path("~/.hermes/cservice")
    cservice_jwt_secret: str = ""
    cservice_jwt_algorithm: str = "HS256"
    cservice_service_token: str = ""
    cservice_wecom_corp_id: str = ""
    cservice_wecom_secret: str = ""
    cservice_kf_callback_token: str = ""
    cservice_kf_callback_aes_key: str = ""
    cservice_hermes_ws_path: str = "/ws/hermes"
    host: str = "127.0.0.1"
    port: int = 8093

    def wecom_configured(self) -> bool:
        return bool(
            self.cservice_wecom_corp_id
            and self.cservice_wecom_secret
            and self.cservice_kf_callback_token
            and self.cservice_kf_callback_aes_key
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
