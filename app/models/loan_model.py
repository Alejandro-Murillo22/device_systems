from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.database import Base


class Loan(Base):
    __tablename__ = "loans"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'returned', 'overdue')", name="ck_loans_status"),
        CheckConstraint("(status = 'returned' AND return_date IS NOT NULL) OR (status != 'returned' AND return_date IS NULL)", name="ck_loans_return_status"),
        CheckConstraint("return_date IS NULL OR return_date >= loan_date", name="ck_loans_dates"),
        Index("uq_loans_open_device", "device_id", unique=True, sqlite_where=text("status IN ('active', 'overdue')")),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="RESTRICT"), index=True)
    loan_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    return_date: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active", index=True)
    user = relationship("User", back_populates="loans")
    device = relationship("Device", back_populates="loans")
