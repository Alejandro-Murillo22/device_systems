from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(str, Enum):
    ADMIN = "admin"
    SUPPORT = "support"
    USER = "user"


class UserBase(BaseModel):
    name: str = Field(
        ...,
        min_length=3,
        max_length=80,
        description="Nombre completo del usuario. Mínimo 3 caracteres.",
        examples=["Nombre Apellido"],
    )
    email: EmailStr = Field(
        ...,
        description="Correo electrónico único del usuario.",
        examples=["usuario@ejemplo.com"],
    )
    role: UserRole = Field(
        default=UserRole.USER,
        description="Rol del usuario: admin, support o user.",
    )
    is_active: bool = Field(
        default=True,
        description="Indica si el usuario está activo.",
    )


class UserCreate(UserBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Nombre Apellido",
                "email": "usuario@ejemplo.com",
                "role": "admin",
                "is_active": True,
            }
        }
    )


class UserUpdate(BaseModel):
    name: str = Field(..., min_length=3, max_length=80)
    email: EmailStr = Field(...)
    role: UserRole = Field(...)
    is_active: bool = Field(...)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Nombre Apellido",
                "email": "usuario@ejemplo.com",
                "role": "admin",
                "is_active": True,
            }
        }
    )


class UserPatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=3, max_length=80)
    email: Optional[EmailStr] = Field(default=None)
    role: Optional[UserRole] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)

    model_config = ConfigDict(
        json_schema_extra={"example": {"role": "support"}}
    )


class UserPublic(UserBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    total: int = Field(..., description="Cantidad de usuarios retornados.")
    items: list[UserPublic] = Field(..., description="Lista de usuarios.")


class ErrorResponse(BaseModel):
    detail: str