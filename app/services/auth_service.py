from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import User
from app.schemas.auth_schema import RegisterRequest
from app.security import dummy_password_hash, hash_password, verify_password


def register_user(db: Session, payload: RegisterRequest) -> User:
    email = str(payload.email).lower()
    if db.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise HTTPException(400, "El correo ya está registrado")
    user = User(name=payload.name, email=email, role="user", is_active=True,
                hashed_password=hash_password(payload.password.get_secret_value()))
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(400, "El correo ya está registrado") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(500, "No se pudo registrar el usuario") from exc
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))
    stored_hash = user.hashed_password if user and user.hashed_password else dummy_password_hash()
    valid = verify_password(password, stored_hash)
    if not valid or user is None or not user.hashed_password:
        raise HTTPException(401, "Correo o contraseña incorrectos", headers={"WWW-Authenticate": "Bearer"})
    if not user.is_active:
        raise HTTPException(403, "Usuario inactivo")
    return user
