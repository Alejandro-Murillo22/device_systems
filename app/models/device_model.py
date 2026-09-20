from datetime import datetime
from sqlalchemy import Boolean, CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.database import Base


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_devices_name"),
        CheckConstraint("length(trim(serial_number)) > 0", name="ck_devices_serial"),
        CheckConstraint("length(trim(device_type)) > 0", name="ck_devices_type"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    serial_number: Mapped[str] = mapped_column(String(100), unique=True)
    device_type: Mapped[str] = mapped_column(String(50), index=True)
    brand: Mapped[str | None] = mapped_column(String(80))
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    loans = relationship("Loan", back_populates="device", passive_deletes="all")
