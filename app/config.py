"""Configuración validada, compartida por seguridad y middleware."""
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)
    environment: Literal["development", "staging", "production"] = "development"
    secret_key: SecretStr = Field(min_length=32)
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)
    allowed_origins: list[str] = Field(default_factory=lambda: [
        "http://localhost:3000", "http://localhost:5173", "http://localhost:4200",
        "http://127.0.0.1:3000", "http://127.0.0.1:5173",
    ])
    allowed_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1", "testserver"])
    https_redirect: bool = False
    api_version: str = "5.0.0"

    @field_validator("allowed_origins", "allowed_hosts", mode="before")
    @classmethod
    def parse_json_list(cls, value):
        return json.loads(value) if isinstance(value, str) else value

    @field_validator("allowed_origins")
    @classmethod
    def explicit_origins(cls, origins):
        for origin in origins:
            parsed = urlsplit(origin)
            if (parsed.scheme not in {"http", "https"} or not parsed.netloc
                    or parsed.path or parsed.query or parsed.fragment
                    or parsed.username or parsed.password or "*" in origin):
                raise ValueError("CORS requiere orígenes explícitos sin ruta, credenciales ni comodines")
        return origins

    @field_validator("allowed_hosts")
    @classmethod
    def explicit_hosts(cls, hosts):
        if not hosts or any(not host or "*" in host or "/" in host for host in hosts):
            raise ValueError("ALLOWED_HOSTS requiere hosts explícitos")
        return hosts

    @model_validator(mode="after")
    def production_origins(self):
        if self.environment != "development":
            if not self.allowed_origins or any(not origin.startswith("https://") for origin in self.allowed_origins):
                raise ValueError("Staging y producción requieren ALLOWED_ORIGINS con HTTPS")
        return self


@lru_cache
def get_settings() -> Settings:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    fields = {
        "environment": "ENVIRONMENT", "secret_key": "SECRET_KEY",
        "access_token_expire_minutes": "ACCESS_TOKEN_EXPIRE_MINUTES",
        "allowed_origins": "ALLOWED_ORIGINS", "allowed_hosts": "ALLOWED_HOSTS",
        "https_redirect": "HTTPS_REDIRECT", "api_version": "API_VERSION",
    }
    return Settings.model_validate({field: os.environ[name] for field, name in fields.items() if name in os.environ})
