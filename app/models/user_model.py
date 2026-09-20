from sqlalchemy import Boolean, CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


class User(Base):
    __tablename__ = "users"
    loans = relationship("Loan", back_populates="user", passive_deletes="all")

    __table_args__ = (
        CheckConstraint("length(trim(name)) >= 3", name="ck_users_name_min_length"),
        CheckConstraint("length(name) <= 80", name="ck_users_name_max_length"),
        CheckConstraint("length(email) <= 254", name="ck_users_email_max_length"),
        CheckConstraint("role IN ('admin', 'support', 'user')", name="ck_users_role_allowed"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True, index=True)
    # NULL conserva cuentas de actividades anteriores sin asignar contraseñas conocidas.
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    internal_notes: Mapped[str] = mapped_column(
        String(255), nullable=False, default="creado automáticamente por device_systems"
    )
