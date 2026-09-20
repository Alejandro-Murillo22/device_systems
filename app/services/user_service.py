"""
Capa de servicios (lógica de negocio) para el recurso users con SQLAlchemy.
"""

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.user_model import User
from app.models.loan_model import Loan
from app.security import hash_password
from app.schemas.user_schema import UserCreate, UserPatch, UserPublic, UserRole, UserUpdate


def _to_public(user: User) -> UserPublic:
    """Convierte la entidad SQLAlchemy al esquema de respuesta público."""
    return UserPublic.model_validate(user)


def list_users(
    db: Session,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
) -> list[UserPublic]:
    query = select(User).order_by(User.id)
    if role is not None:
        query = query.where(User.role == role.value)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    users = db.scalars(query).all()
    return [_to_public(user) for user in users]


def email_in_use(
    db: Session,
    email: str,
    exclude_id: Optional[int] = None,
) -> bool:
    """
    Revisa si un correo ya existe en la base de datos.
    `exclude_id` permite ignorar al propio usuario en actualizaciones.
    """
    normalized = str(email).strip().lower()
    query = select(User.id).where(func.lower(User.email) == normalized)
    if exclude_id is not None:
        query = query.where(User.id != exclude_id)
    return db.scalar(query) is not None


def create_user(db: Session, payload: UserCreate) -> UserPublic:
    normalized_email = str(payload.email).strip().lower()
    if email_in_use(db, normalized_email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El correo '{normalized_email}' ya está registrado",
        )

    user = User(
        name=payload.name.strip(),
        email=normalized_email,
        role=payload.role.value,
        is_active=payload.is_active,
        hashed_password=hash_password(payload.password.get_secret_value()) if payload.password else None,
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo crear el usuario porque uno de los datos viola una restricción de la base de datos",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo guardar el usuario en la base de datos",
        ) from exc
    return _to_public(user)


def replace_user(db: Session, user: User, payload: UserUpdate) -> UserPublic:
    """Actualización TOTAL (PUT): reemplaza todos los campos del usuario."""
    normalized_email = str(payload.email).strip().lower()
    if email_in_use(db, normalized_email, exclude_id=user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El correo '{normalized_email}' ya está registrado",
        )

    user.name = payload.name.strip()
    user.email = normalized_email
    user.role = payload.role.value
    user.is_active = payload.is_active
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo actualizar el usuario porque uno de los datos viola una restricción de la base de datos",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo actualizar el usuario en la base de datos",
        ) from exc
    return _to_public(user)


def update_user_partial(db: Session, user: User, payload: UserPatch) -> UserPublic:
    """Actualización PARCIAL (PATCH): solo aplica los campos enviados."""
    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe enviar al menos un campo para actualizar",
        )

    if "email" in changes and changes["email"] is not None:
        normalized_email = str(changes["email"]).strip().lower()
        if email_in_use(db, normalized_email, exclude_id=user.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El correo '{normalized_email}' ya está registrado",
            )
        user.email = normalized_email

    if "name" in changes and changes["name"] is not None:
        user.name = changes["name"].strip()
    if "role" in changes and changes["role"] is not None:
        user.role = changes["role"].value
    if "is_active" in changes and changes["is_active"] is not None:
        user.is_active = changes["is_active"]

    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo actualizar el usuario porque uno de los datos viola una restricción de la base de datos",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo actualizar el usuario en la base de datos",
        ) from exc
    return _to_public(user)


def delete_user(db: Session, user: User) -> None:
    if db.scalar(select(Loan.id).where(Loan.user_id == user.id)):
        raise HTTPException(409, "El usuario tiene historial de préstamos")
    db.delete(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "El usuario tiene préstamos asociados") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo eliminar el usuario de la base de datos",
        ) from exc
