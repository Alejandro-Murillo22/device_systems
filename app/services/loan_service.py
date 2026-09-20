from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import contains_eager
from app.models import Device, Loan, User
from app.services.device_service import get_device


def get_loan(db, loan_id):
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(404, "Préstamo no encontrado")
    return loan


def create_loan(db, payload):
    if db.get(User, payload.user_id) is None:
        raise HTTPException(404, "Usuario no encontrado")
    get_device(db, payload.device_id)
    try:
        claimed = db.execute(update(Device).where(Device.id == payload.device_id, Device.is_available.is_(True)).values(is_available=False))
        if claimed.rowcount != 1:
            db.rollback()
            raise HTTPException(409, "Dispositivo no disponible")
        loan = Loan(user_id=payload.user_id, device_id=payload.device_id)
        db.add(loan)
        db.commit()
        db.refresh(loan)
        return loan
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "El dispositivo ya está prestado o la referencia dejó de existir") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(500, "No se pudo registrar el préstamo") from exc


def return_loan(db, loan_id):
    loan = get_loan(db, loan_id)
    try:
        changed = db.execute(update(Loan).where(Loan.id == loan_id, Loan.status.in_(["active", "overdue"])).values(status="returned", return_date=datetime.now(timezone.utc).replace(tzinfo=None)))
        if changed.rowcount != 1:
            db.rollback()
            raise HTTPException(409, "El préstamo ya fue devuelto")
        db.execute(update(Device).where(Device.id == loan.device_id).values(is_available=True))
        db.commit()
        db.refresh(loan)
        return loan
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(500, "No se pudo devolver el préstamo") from exc


def list_loans(db, user_id=None, device_id=None, status=None, user_email=None, device_type=None, search=None, date_from=None, date_to=None):
    query = select(Loan).join(Loan.user).join(Loan.device).options(contains_eager(Loan.user), contains_eager(Loan.device)).order_by(Loan.id)
    conditions = []
    for column, value in ((Loan.user_id, user_id), (Loan.device_id, device_id), (Loan.status, status), (Device.device_type, device_type)):
        if value is not None:
            conditions.append(column == value)
    if user_email:
        conditions.append(User.email == str(user_email).lower())
    if search:
        conditions.append(or_(User.name.icontains(search, autoescape=True), User.email.icontains(search, autoescape=True), Device.name.icontains(search, autoescape=True)))
    if date_from:
        conditions.append(Loan.loan_date >= date_from)
    if date_to:
        conditions.append(Loan.loan_date <= date_to)
    if conditions:
        query = query.where(and_(*conditions))
    return db.scalars(query).all()
