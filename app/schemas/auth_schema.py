from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator
from app.security import validate_password_size


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=3, max_length=80, examples=["Ana Perez"])
    email: EmailStr = Field(examples=["ana@example.com"])
    password: SecretStr = Field(min_length=8, max_length=72, description="8 caracteres como mínimo; 72 bytes UTF-8 como máximo", examples=["ClaveEjemplo2026!"])

    @field_validator("name", "email", mode="before")
    @classmethod
    def strip_fields(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def password_bytes(cls, value):
        validate_password_size(value.get_secret_value())
        return value


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(gt=0, description="Vigencia del token en segundos")
