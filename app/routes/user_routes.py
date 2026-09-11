from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies.user_dependencies import (
    active_filter,
    get_user_or_404,
    role_filter,
    verify_api_key,
)
from app.models.user_model import User
from app.schemas.user_schema import (
    UserCreate,
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
    description="Retorna todos los usuarios y permite filtrar por rol y estado.",
    response_description="Listado de usuarios.",
)
def list_users(
    role: Optional[UserRole] = Depends(role_filter),
    is_active: Optional[bool] = Depends(active_filter),
    db: Session = Depends(get_db),
) -> UserListResponse:
    items = user_service.list_users(db, role=role, is_active=is_active)
    return UserListResponse(total=len(items), items=items)


@router.get(
    "/{user_id}",
    response_model=UserPublic,
    summary="Consultar usuario por ID",
    description="Retorna un usuario a partir de su ID.",
    response_description="Datos públicos del usuario.",
    responses={404: {"description": "Usuario no encontrado"}},
)
def get_user(user: User = Depends(get_user_or_404)) -> UserPublic:
    return UserPublic.model_validate(user)


@router.post(
    "",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo usuario",
    description="Crea un usuario en la base de datos con validación Pydantic y restricciones SQLAlchemy.",
    response_description="Usuario creado.",
    responses={400: {"description": "Correo duplicado o restricción de base de datos"}},
)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
) -> UserPublic:
    return user_service.create_user(db, payload)


@router.put(
    "/{user_id}",
    response_model=UserPublic,
    summary="Actualizar usuario",
    description="Reemplaza todos los campos del usuario existente.",
    response_description="Usuario actualizado.",
    responses={
        400: {"description": "Correo duplicado o restricción de base de datos"},
        404: {"description": "Usuario no encontrado"},
    },
)
def replace_user(
    payload: UserUpdate,
    user: User = Depends(get_user_or_404),
    db: Session = Depends(get_db),
) -> UserPublic:
    return user_service.replace_user(db, user, payload)


@router.patch(
    "/{user_id}",
    response_model=UserPublic,
    summary="Actualizar usuario parcialmente",
    description="Modifica solamente los campos enviados en el body.",
    response_description="Usuario actualizado.",
    responses={
        400: {"description": "Sin campos, correo duplicado o restricción de base de datos"},
        404: {"description": "Usuario no encontrado"},
    },
)
def update_user(
    payload: UserPatch,
    user: User = Depends(get_user_or_404),
    db: Session = Depends(get_db),
) -> UserPublic:
    return user_service.update_user_partial(db, user, payload)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar usuario",
    description="Elimina un usuario existente. Requiere la cabecera X-API-Key.",
    response_description="Confirmación de eliminación.",
    responses={
        401: {"description": "API Key inválida o ausente"},
        404: {"description": "Usuario no encontrado"},
    },
    dependencies=[Depends(verify_api_key)],
)
def delete_user(
    user: User = Depends(get_user_or_404),
    db: Session = Depends(get_db),
) -> dict:
    user_id = user.id
    user_service.delete_user(db, user)
    return {"detail": f"Usuario con id {user_id} eliminado correctamente"}