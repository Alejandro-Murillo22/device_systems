"""
Rutas HTTP del recurso "users" para device_systems.

Este archivo SOLO define endpoints: recibe la petición, delega en
`user_service` la lógica real, y devuelve el resultado. La validación de
"usuario no existe" y los filtros de query quedan resueltos por las
dependencias de `user_dependencies` antes de que el cuerpo de cada función
se ejecute.
"""

from typing import Optional

from fastapi import APIRouter, Depends, status

from app.dependencies.user_dependencies import (
    active_filter,
    get_user_or_404,
    role_filter,
    verify_api_key,
)
from app.schemas.user_schema import (
    UserCreate,
    UserInDB,
    UserListResponse,
    UserPatch,
    UserPublic,
    UserRole,
    UserUpdate,
)
from app.services import user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "",
    response_model=UserListResponse,
    summary="Listar usuarios",
    description="Retorna todos los usuarios. Permite filtrar opcionalmente "
    "por rol (`role`) y por estado activo (`is_active`).",
    response_description="Listado de usuarios (total + items).",
)
def list_users(
    role: Optional[UserRole] = Depends(role_filter),
    is_active: Optional[bool] = Depends(active_filter),
) -> UserListResponse:
    items = user_service.list_users(role=role, is_active=is_active)
    return UserListResponse(total=len(items), items=items)


@router.get(
    "/{user_id}",
    response_model=UserPublic,
    summary="Consultar usuario por ID",
    description="Retorna un único usuario a partir de su ID. Si no existe, "
    "responde 404 (resuelto por la dependencia get_user_or_404).",
    response_description="Datos públicos del usuario.",
    responses={404: {"description": "Usuario no encontrado"}},
)
def get_user(user: UserInDB = Depends(get_user_or_404)) -> UserPublic:
    return UserPublic(**user.model_dump())


@router.post(
    "",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo usuario",
    description="Crea un nuevo usuario validando los datos con Pydantic. "
    "Evita correos electrónicos duplicados.",
    response_description="Usuario creado.",
    responses={400: {"description": "El correo ya está registrado"}},
)
def create_user(payload: UserCreate) -> UserPublic:
    return user_service.create_user(payload)


@router.put(
    "/{user_id}",
    response_model=UserPublic,
    summary="Actualizar usuario (reemplazo completo)",
    description="Reemplaza TODOS los campos del usuario existente. Los "
    "cuatro campos (name, email, role, is_active) son obligatorios.",
    response_description="Usuario actualizado.",
    responses={
        400: {"description": "El correo ya está registrado"},
        404: {"description": "Usuario no encontrado"},
    },
)
def replace_user(
    payload: UserUpdate, user: UserInDB = Depends(get_user_or_404)
) -> UserPublic:
    return user_service.replace_user(user.id, payload)


@router.patch(
    "/{user_id}",
    response_model=UserPublic,
    summary="Actualizar usuario (parcial)",
    description="Modifica solo los campos enviados en el body. Si no se "
    "envía ningún campo, responde 400.",
    response_description="Usuario actualizado con los campos modificados.",
    responses={
        400: {"description": "Sin campos para actualizar o correo duplicado"},
        404: {"description": "Usuario no encontrado"},
    },
)
def update_user(
    payload: UserPatch, user: UserInDB = Depends(get_user_or_404)
) -> UserPublic:
    return user_service.update_user_partial(user.id, payload)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar usuario",
    description="Elimina un usuario existente. Requiere la cabecera "
    "`X-API-Key` (simulación de autenticación básica).",
    response_description="Confirmación de eliminación.",
    responses={
        401: {"description": "API Key inválida o ausente"},
        404: {"description": "Usuario no encontrado"},
    },
    dependencies=[Depends(verify_api_key)],
)
def delete_user(user: UserInDB = Depends(get_user_or_404)) -> dict:
    user_service.delete_user(user.id)
    return {"detail": f"Usuario con id {user.id} eliminado correctamente"}
