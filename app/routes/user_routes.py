from typing import Optional

from fastapi import APIRouter, Depends, Response, status
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
from app.schemas.loan_schema import LoanDetailResponse
from app.schemas.device_schema import DeviceResponse
from app.services import loan_service
from app.dependencies.auth_dependencies import get_current_active_user, require_admin, require_staff

router = APIRouter(prefix="/users", tags=["Users"], dependencies=[Depends(get_current_active_user)], responses={401: {"description": "JWT ausente o inválido"}, 403: {"description": "Permisos insuficientes"}})


@router.get(
    "",
    response_model=UserListResponse,
    summary="Listar usuarios",
    description="Retorna todos los usuarios y permite filtrar por rol y estado.",
    response_description="Listado de usuarios.",
    dependencies=[Depends(require_staff)],
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
    dependencies=[Depends(require_admin)],
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
    dependencies=[Depends(require_admin)],
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
    dependencies=[Depends(require_admin)],
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
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar usuario",
    description="Elimina un usuario existente. Requiere la cabecera X-API-Key.",
    response_description="Confirmación de eliminación.",
    responses={
        401: {"description": "API Key inválida o ausente"},
        404: {"description": "Usuario no encontrado"},
        409: {"description": "Usuario con historial de préstamos"},
    },
    dependencies=[Depends(require_admin), Depends(verify_api_key)],
)
def delete_user(
    user: User = Depends(get_user_or_404),
    db: Session = Depends(get_db),
) -> Response:
    user_service.delete_user(db, user)
    return Response(status_code=204)


@router.get("/{user_id}/loans", response_model=list[LoanDetailResponse], summary="Préstamos del usuario", description="Consulta con joins el historial del usuario.", response_description="Préstamos y equipos relacionados")
def user_loans(user: User = Depends(get_user_or_404), db: Session = Depends(get_db)):
    return loan_service.list_loans(db, user_id=user.id)


@router.get("/{user_id}/devices", response_model=list[DeviceResponse], summary="Dispositivos asignados", description="Equipos con préstamos active u overdue del usuario.", response_description="Dispositivos actualmente asignados")
def user_devices(user: User = Depends(get_user_or_404), db: Session = Depends(get_db)):
    return [loan.device for loan in loan_service.list_loans(db, user_id=user.id) if loan.status != "returned"]
