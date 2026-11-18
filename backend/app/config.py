from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _empty_to_none(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    keitaro_base_url: str = "https://tlgk.host"
    keitaro_api_key: str = ""
    keitaro_domain_id: int | None = None
    keitaro_group_id: int | None = None
    keitaro_traffic_source_id: int | None = None

    @field_validator(
        "keitaro_domain_id",
        "keitaro_group_id",
        "keitaro_traffic_source_id",
        mode="before",
    )
    @classmethod
    def optional_int(cls, value: Any) -> Any:
        return _empty_to_none(value)

    database_url: str = "sqlite:///./keitaro_wrapper.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def keitaro_api_base(self) -> str:
        return self.keitaro_base_url.rstrip("/") + "/admin_api/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
