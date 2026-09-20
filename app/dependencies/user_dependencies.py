import os
from typing import Optional

from fastapi import Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.user_model import User
from app.schemas.user_schema import UserRole
from app.dependencies.auth_dependencies import get_current_active_user, require_owner_or_staff


def get_user_or_404(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Busca un usuario por ID en la BD y lanza 404 si no existe."""
    require_owner_or_staff(user_id, current_user)
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )
    return user


def role_filter(
    role: Optional[UserRole] = Query(
        default=None,
        description="Filtra usuarios por rol: admin, support o user.",
    )
) -> Optional[UserRole]:
    """Encapsula el query param `role` para reutilizarlo como dependencia."""
    return role


def active_filter(
    is_active: Optional[bool] = Query(
        default=None,
        description="Filtra usuarios por estado activo/inactivo.",
    )
) -> Optional[bool]:
    """Encapsula el query param `is_active` para reutilizarlo como dependencia."""
    return is_active


def get_api_settings() -> dict:
    """Ejemplo de dependencia que entrega configuración general de la API."""
    return {
        "app_name": "device_systems",
        "version": os.getenv("API_VERSION", "5.0.0"),
    }


def verify_api_key(
    x_api_key: Optional[str] = Header(
        default=None,
        alias="X-API-Key",
        description="Clave simulada de autenticación para operaciones sensibles.",
    )
) -> str:
    """Simula una autenticación básica leyendo una cabecera personalizada."""
    expected_key = os.getenv("API_KEY", "device_systems_key")
    if x_api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida o no proporcionada",
        )
    return x_api_key
