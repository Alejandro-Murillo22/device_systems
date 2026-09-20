from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.models import Device, Loan


def get_device(db, device_id):
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(404, "Dispositivo no encontrado")
    return device


def commit(db, duplicate_message="Número de serie duplicado"):
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(400, duplicate_message) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(500, "Error interno de base de datos") from exc


def list_devices(db, device_type=None, is_available=None, brand=None, search=None):
    query = select(Device).order_by(Device.id)
    for column, value in ((Device.device_type, device_type), (Device.is_available, is_available), (Device.brand, brand)):
        if value is not None:
            query = query.where(column == value)
    if search:
        query = query.where(or_(Device.name.icontains(search, autoescape=True), Device.serial_number.icontains(search, autoescape=True)))
    return db.scalars(query).all()


def create_device(db, payload):
    device = Device(**payload.model_dump())
    db.add(device)
    commit(db)
    db.refresh(device)
    return device


def update_device(db, device, payload, partial=False):
    changes = payload.model_dump(exclude_unset=partial)
    if not changes:
        raise HTTPException(400, "Debe enviar al menos un campo para actualizar")
    # Bloquear modificaciones mientras exista un préstamo abierto evita alterar disponibilidad.
    if db.scalar(select(Loan.id).where(Loan.device_id == device.id, Loan.status != "returned")):
        raise HTTPException(409, "No se puede modificar un dispositivo prestado")
    for field, value in changes.items():
        setattr(device, field, value)
    commit(db)
    db.refresh(device)
    return device


def delete_device(db, device):
    if db.scalar(select(Loan.id).where(Loan.device_id == device.id)):
        raise HTTPException(409, "El dispositivo tiene historial de préstamos")
    db.delete(device)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "El dispositivo tiene préstamos asociados") from exc
