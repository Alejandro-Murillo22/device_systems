from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models import User
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_current_user(request: Request, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        user_id = decode_access_token(token, request.app.state.settings)
    except (JWTError, ValueError, TypeError) as exc:
        raise HTTPException(401, "No se pudieron validar las credenciales", headers={"WWW-Authenticate": "Bearer"}) from exc
    user = db.get(User, user_id)
    if user is None or not user.hashed_password:
        raise HTTPException(401, "No se pudieron validar las credenciales", headers={"WWW-Authenticate": "Bearer"})
    return user


def get_current_active_user(request: Request, user: User = Depends(get_current_user)) -> User:
    if not user.is_active:
        raise HTTPException(403, "Usuario inactivo")
    request.state.user_id = user.id
    return user


def require_admin(user: User = Depends(get_current_active_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Se requiere rol admin")
    return user


def require_staff(user: User = Depends(get_current_active_user)) -> User:
    if user.role not in {"admin", "support"}:
        raise HTTPException(403, "Se requiere rol admin o support")
    return user


def require_owner_or_staff(owner_id: int, user: User) -> None:
    if user.id != owner_id and user.role not in {"admin", "support"}:
        raise HTTPException(403, "No tiene permiso para consultar o modificar este recurso")
