"""
Esquemas Pydantic para el recurso "users" de device_systems.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(str, Enum):
    """Roles permitidos para un usuario del sistema device_systems."""

    ADMIN = "admin"
    SUPPORT = "support"
    USER = "user"


class UserBase(BaseModel):
    """Campos comunes compartidos entre los distintos esquemas de usuario."""

    name: str = Field(
        ...,
        min_length=3,
        max_length=80,
        description="Nombre completo del usuario. Mínimo 3 caracteres.",
        examples=["Alejandro Murillo"],
    )
    email: EmailStr = Field(
        ...,
        description="Correo electrónico único del usuario.",
        examples=["alejandro@device-systems.com"],
    )
    role: UserRole = Field(
        default=UserRole.USER,
        description="Rol del usuario dentro del sistema: admin, support o user.",
    )
    is_active: bool = Field(
        default=True,
        description="Indica si el usuario se encuentra activo en el sistema.",
    )


class UserCreate(UserBase):
    """Esquema de entrada utilizado en POST /users."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Alejandro Murillo",
                "email": "alejandro@device-systems.com",
                "role": "admin",
                "is_active": True,
            }
        }
    )


class UserUpdate(BaseModel):
    """
    Esquema de entrada utilizado en PUT /users/{user_id}.

    A diferencia de UserBase, aquí `role` e `is_active` NO tienen valor por
    defecto: los cuatro campos son obligatorios porque un PUT reemplaza por
    completo al usuario existente (actualización total).
    """

    name: str = Field(..., min_length=3, max_length=80)
    email: EmailStr = Field(...)
    role: UserRole = Field(...)
    is_active: bool = Field(...)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Alejandro Murillo",
                "email": "alejandro@device-systems.com",
                "role": "admin",
                "is_active": True,
            }
        }
    )


class UserPatch(BaseModel):
    """
    Esquema de entrada utilizado en PATCH /users/{user_id}.

    Todos los campos son opcionales (default=None) porque el cliente solo
    envía los que quiere modificar.
    """

    name: Optional[str] = Field(default=None, min_length=3, max_length=80)
    email: Optional[EmailStr] = Field(default=None)
    role: Optional[UserRole] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)

    model_config = ConfigDict(
        json_schema_extra={"example": {"role": "support"}}
    )


class UserInDB(UserBase):
    """
    Representación interna/completa del usuario para la base de datos.
    Incluye campos de auditoría como `internal_notes`.
    """

    id: int
    internal_notes: str = Field(
        default="creado automáticamente por device_systems",
        description="Campo interno de auditoría. No se expone en la API pública.",
    )


class UserPublic(UserBase):
    """
    Response model utilizado por los endpoints de la API pública.
    """

    id: int

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Alejandro Murillo",
                "email": "alejandro@device-systems.com",
                "role": "admin",
                "is_active": True,
            }
        },
    )


class UserListResponse(BaseModel):
    """Envoltorio estandarizado para la respuesta de listado de usuarios."""

    total: int = Field(..., description="Cantidad total de usuarios retornados.")
    items: list[UserPublic] = Field(..., description="Lista de usuarios.")


class ErrorResponse(BaseModel):
    """Esquema estándar para respuestas de error."""

    detail: str