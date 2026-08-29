"""
Capa de servicios (lógica de negocio) para el recurso users.

Las rutas (routes/user_routes.py) NO deben contener lógica de negocio
directamente: solo reciben la petición HTTP, llaman a estas funciones, y
devuelven lo que ellas retornan. Esto permite, por ejemplo, reutilizar
`create_user` desde un futuro script de importación masiva sin pasar por
HTTP, o cambiar la validación de correos duplicados en un solo lugar.
"""

from typing import Optional

from fastapi import HTTPException, status

from app.data.users_db import get_next_id, users_db
from app.schemas.user_schema import (
    UserCreate,
    UserInDB,
    UserPatch,
    UserPublic,
    UserRole,
    UserUpdate,
)


def _to_public(user: UserInDB) -> UserPublic:
    """Convierte el modelo interno (con internal_notes) al modelo público."""
    return UserPublic(**user.model_dump())


def list_users(
    role: Optional[UserRole] = None, is_active: Optional[bool] = None
) -> list[UserPublic]:
    results = list(users_db.values())

    if role is not None:
        results = [u for u in results if u.role == role]

    if is_active is not None:
        results = [u for u in results if u.is_active == is_active]

    return [_to_public(u) for u in results]


def email_in_use(email: str, exclude_id: Optional[int] = None) -> bool:
    """
    Revisa si un correo ya existe en la base de datos.

    `exclude_id` permite ignorar al propio usuario que se está actualizando
    (si no lo excluyéramos, un PUT/PATCH que no cambia el correo se
    rechazaría a sí mismo por "duplicado").
    """
    normalized = email.lower()
    for existing in users_db.values():
        if existing.id == exclude_id:
            continue
        if existing.email.lower() == normalized:
            return True
    return False


def create_user(payload: UserCreate) -> UserPublic:
    if email_in_use(payload.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El correo '{payload.email}' ya está registrado",
        )

    new_id = get_next_id()
    new_user = UserInDB(
        id=new_id,
        name=payload.name,
        email=payload.email,
        role=payload.role,
        is_active=payload.is_active,
    )
    users_db[new_id] = new_user
    return _to_public(new_user)


def replace_user(user_id: int, payload: UserUpdate) -> UserPublic:
    """Actualización TOTAL (PUT): reemplaza todos los campos del usuario."""
    existing = users_db[user_id]  

    if email_in_use(payload.email, exclude_id=user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El correo '{payload.email}' ya está registrado",
        )

    updated = UserInDB(
        id=user_id,
        name=payload.name,
        email=payload.email,
        role=payload.role,
        is_active=payload.is_active,
        internal_notes=existing.internal_notes, 
    )
    users_db[user_id] = updated
    return _to_public(updated)


def update_user_partial(user_id: int, payload: UserPatch) -> UserPublic:
    """Actualización PARCIAL (PATCH): solo aplica los campos enviados."""
    existing = users_db[user_id]


    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe enviar al menos un campo para actualizar",
        )

    if "email" in changes and email_in_use(changes["email"], exclude_id=user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El correo '{changes['email']}' ya está registrado",
        )

    merged_data = existing.model_dump()
    merged_data.update(changes)
    updated = UserInDB(**merged_data)
    users_db[user_id] = updated
    return _to_public(updated)


def delete_user(user_id: int) -> None:
    del users_db[user_id]  
