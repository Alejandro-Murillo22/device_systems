"""
Rutas del recurso "users" para device_systems.

Implementa:
- GET  /users                -> listar usuarios (con filtros opcionales por
                                 query params: role, is_active)
- GET  /users/{user_id}      -> consultar un usuario por Path Parameter
- POST /users                -> registrar un nuevo usuario (valida email
                                 duplicado y retorna response_model)
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.schemas.user_schema import (
    UserCreate,
    UserInDB,
    UserListResponse,
    UserPublic,
    UserRole,
)

router = APIRouter(prefix="/users", tags=["Users"])

# ---------------------------------------------------------------------------
# "Base de datos" en memoria (solo para efectos de la actividad académica).
# Se inicializa con datos semilla para poder probar los GET de inmediato.
# ---------------------------------------------------------------------------
_users_db: dict[int, UserInDB] = {
    1: UserInDB(
        id=1,
        name="Alejandro Ramirez",
        email="alejandro@device-systems.com",
        role=UserRole.ADMIN,
        is_active=True,
    ),
    2: UserInDB(
        id=2,
        name="Juan Duque",
        email="juan@device-systems.com",
        role=UserRole.SUPPORT,
        is_active=True,
    ),
    3: UserInDB(
        id=3,
        name="Mateo Gomez",
        email="mateo@device-systems.com",
        role=UserRole.USER,
        is_active=False,
    ),
}
_next_id = 4


@router.get(
    "",
    response_model=UserListResponse,
    summary="Listar usuarios",
    description="Retorna todos los usuarios. Permite filtrar opcionalmente "
    "por rol (`role`) y por estado activo (`is_active`) usando Query "
    "Parameters.",
)
def list_users(
    response: Response,
    role: Optional[UserRole] = Query(
        default=None, description="Filtra usuarios por rol: admin, support o user."
    ),
    is_active: Optional[bool] = Query(
        default=None, description="Filtra usuarios por estado activo/inactivo."
    ),
) -> UserListResponse:
    results = list(_users_db.values())

    if role is not None:
        results = [u for u in results if u.role == role]

    if is_active is not None:
        results = [u for u in results if u.is_active == is_active]

    response.headers["X-App-Name"] = "device_systems"
    response.headers["X-API-Version"] = "1.0"

    public_users = [UserPublic(**u.model_dump()) for u in results]
    return UserListResponse(total=len(public_users), items=public_users)


@router.get(
    "/{user_id}",
    response_model=UserPublic,
    summary="Consultar usuario por ID",
    description="Retorna un único usuario a partir de su ID (Path Parameter). "
    "Si no existe, retorna 404.",
    responses={404: {"description": "Usuario no encontrado"}},
)
def get_user(user_id: int, response: Response) -> UserPublic:
    user = _users_db.get(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con id {user_id} no encontrado",
        )

    response.headers["X-App-Name"] = "device_systems"
    response.headers["X-API-Version"] = "1.0"

    return UserPublic(**user.model_dump())


@router.post(
    "",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo usuario",
    description="Crea un nuevo usuario validando los datos con Pydantic. "
    "Evita correos electrónicos duplicados.",
    responses={409: {"description": "El correo ya está registrado"}},
)
def create_user(payload: UserCreate, response: Response) -> UserPublic:
    global _next_id

    email_normalized = payload.email.lower()
    for existing in _users_db.values():
        if existing.email.lower() == email_normalized:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El correo '{payload.email}' ya está registrado",
            )

    new_user = UserInDB(
        id=_next_id,
        name=payload.name,
        email=payload.email,
        role=payload.role,
        is_active=payload.is_active,
    )
    _users_db[_next_id] = new_user
    _next_id += 1

    response.headers["X-App-Name"] = "device_systems"
    response.headers["X-API-Version"] = "1.0"

    return UserPublic(**new_user.model_dump())
