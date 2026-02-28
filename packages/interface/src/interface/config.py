"""Application configuration via Pydantic Settings."""
from __future__ import annotations
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")
    app_name: str = "AlgoTrading API"
    app_version: str = "0.1.0"
    log_level: str = Field(default="INFO")
    dry_run: bool = Field(default=True)
    db_path: Path = Field(default=Path("data/db/trading.duckdb"))
    cors_origins: str = Field(default="http://localhost:3000")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    ssi_consumer_id: str = Field(default="")
    ssi_consumer_secret: SecretStr = Field(default=SecretStr(""))
    ssi_private_key_b64: SecretStr = Field(default=SecretStr(""))
    ssi_account_no: str = Field(default="")

    @property
    def ssi_configured(self) -> bool:
        return bool(self.ssi_consumer_id and self.ssi_consumer_secret.get_secret_value() and self.ssi_private_key_b64.get_secret_value() and self.ssi_account_no)

    dnse_username: str = Field(default="")
    dnse_password: SecretStr = Field(default=SecretStr(""))
    model_path: Path = Field(default=Path("data/models/phi-3-mini-int4"))
    ai_device: str = Field(default="AUTO")
    max_position_pct: Decimal = Field(default=Decimal("0.20"))
    max_daily_loss: Decimal = Field(default=Decimal("5000000"))
    kill_switch: bool = Field(default=False)
    max_candidates: int = Field(default=10, ge=1, le=50)
    score_threshold: float = Field(default=5.0, ge=0.0, le=10.0)
    telegram_bot_token: str = Field(default="")
    telegram_chat_id: str = Field(default="")


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings()
