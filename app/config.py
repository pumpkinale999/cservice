"""Application settings (CSERVICE_*)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
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
    cservice_demo_outbound: bool = False
    cservice_hermes_ws_path: str = "/ws/hermes"
    cservice_wg_enabled: bool = False
    cservice_wg_auto_register: bool = True
    cservice_wg_broadcast_enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 8093

    @field_validator(
        "cservice_demo_outbound",
        "cservice_wg_enabled",
        "cservice_wg_auto_register",
        "cservice_wg_broadcast_enabled",
        mode="before",
    )
    @classmethod
    def _coerce_bool_flag(cls, v: object) -> bool:
        if isinstance(v, bool):
            return v
        if v is None:
            return False
        return str(v).strip().lower() in ("1", "true", "yes", "on")

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
