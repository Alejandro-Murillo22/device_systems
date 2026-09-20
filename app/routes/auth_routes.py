from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies.auth_dependencies import get_current_active_user
from app.models import User
from app.rate_limit import authenticated_user_key, limiter
from app.schemas.auth_schema import RegisterRequest, Token
from app.schemas.user_schema import UserPublic
from app.security import create_access_token
from app.services.auth_service import authenticate_user, register_user

router = APIRouter(tags=["Auth"], responses={401: {"description": "Credenciales inválidas"}, 403: {"description": "Usuario inactivo"}, 429: {"description": "Límite de peticiones excedido"}})


@router.post("/register", status_code=201, response_model=UserPublic, summary="Registrar cuenta", description="Crea una cuenta activa de rol user; almacena solo el hash bcrypt. Límite: 5/minuto por IP.", response_description="Datos públicos de la cuenta", responses={400: {"description": "Correo duplicado"}})
@limiter.limit("5/minute")
def register(request: Request, response: Response, payload: RegisterRequest, db: Session = Depends(get_db)):
    return register_user(db, payload)


@router.post("/token", response_model=Token, summary="Iniciar sesión OAuth2", description="Formulario: username es el email y password es la contraseña. Límite: 5/minuto por IP.", response_description="JWT y tiempo de vigencia")
@limiter.limit("5/minute")
def login(request: Request, response: Response, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form.username, form.password)
    settings = request.app.state.settings
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return Token(access_token=create_access_token(user.id, settings), expires_in=settings.access_token_expire_minutes * 60)


@router.get("/users/me", response_model=UserPublic, summary="Consultar mi perfil", description="Requiere JWT válido y usuario activo. Límite: 30/minuto por usuario, compartido entre sus tokens.", response_description="Perfil sin contraseña ni hash")
@limiter.limit("30/minute", key_func=authenticated_user_key)
def me(request: Request, response: Response, user: User = Depends(get_current_active_user)):
    return user
