"""
Dependencias reutilizables (Depends()) para device_systems.

Cada función aquí resuelve UNA responsabilidad puntual y se "inyecta" en
las rutas que la necesiten, en vez de repetir la misma lógica en cada
endpoint.
"""

from typing import Optional

from fastapi import Header, HTTPException, Query, status

from app.data.users_db import users_db
from app.schemas.user_schema import UserInDB, UserRole


_API_KEY_ESPERADA = "device_systems_key"


def get_user_or_404(user_id: int) -> UserInDB:
    """
    Busca un usuario por ID y lanza 404 si no existe.

    Se usa en GET /users/{id}, PUT, PATCH y DELETE: los cuatro necesitan
    exactamente esta misma validación antes de hacer su trabajo específico,
    así que se escribe una sola vez aquí.

    FastAPI reconoce `user_id` como Path Parameter automáticamente porque
    el nombre coincide con el de la ruta que usa esta dependencia.
    """
    user = users_db.get(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )
    return user


def role_filter(
    role: Optional[UserRole] = Query(
        default=None, description="Filtra usuarios por rol: admin, support o user."
    )
) -> Optional[UserRole]:
    """Encapsula el query param `role` para reutilizarlo como dependencia."""
    return role


def active_filter(
    is_active: Optional[bool] = Query(
        default=None, description="Filtra usuarios por estado activo/inactivo."
    )
) -> Optional[bool]:
    """Encapsula el query param `is_active` para reutilizarlo como dependencia."""
    return is_active


def get_api_settings() -> dict:
    """
    Ejemplo de dependencia que entrega configuración general de la API.

    Si mañana estos valores vinieran de un archivo .env o de una base de
    datos de configuración, solo se cambiaría esta función, sin tocar a
    quienes la usan.
    """
    return {"app_name": "device_systems", "version": "2.0.0"}


def verify_api_key(
    x_api_key: Optional[str] = Header(
        default=None,
        alias="X-API-Key",
        description="Clave simulada de autenticación para operaciones sensibles.",
    )
) -> str:
    """
    Simula una autenticación básica leyendo una cabecera personalizada.

    El header se declara opcional (default=None) a propósito: si lo
    hiciéramos obligatorio con `...`, FastAPI respondería 422 cuando falta
    por completo, antes de que esta función se ejecute. Al validarlo aquí
    manualmente, tanto "no mandó la cabecera" como "la mandó mal" terminan
    en el mismo 401, que es la respuesta correcta para un fallo de
    autenticación.

    No es seguridad real (la clave está en texto plano en el código, solo
    para fines académicos); demuestra el patrón de Depends() leyendo un
    Header en vez de un Path o Query Parameter. Se aplica en DELETE para
    ejemplificar que un endpoint puede proteger solo la(s) operación(es)
    más sensible(s), no necesariamente todas.
    """
    if x_api_key != _API_KEY_ESPERADA:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida o no proporcionada",
        )
    return x_api_key
