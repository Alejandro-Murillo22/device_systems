from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.schemas.device_schema import DeviceCreate, DeviceUpdate, DevicePatch, DeviceResponse
from app.schemas.loan_schema import LoanDetailResponse
from app.services import device_service as service, loan_service

router = APIRouter(prefix="/devices", tags=["Devices"], responses={404: {"description": "Dispositivo inexistente"}, 400: {"description": "Serie duplicada o actualización vacía"}, 409: {"description": "Dispositivo con préstamos"}})


@router.get("", response_model=list[DeviceResponse], summary="Listar dispositivos", description="Combina filtros por tipo, disponibilidad, marca y búsqueda por nombre o serie.", response_description="Dispositivos que coinciden con los filtros")
def list_devices(device_type: str | None = Query(None, min_length=1), is_available: bool | None = None, brand: str | None = Query(None, min_length=1), search: str | None = Query(None, min_length=1), db: Session = Depends(get_db)):
    return service.list_devices(db, device_type, is_available, brand, search)


@router.post("", response_model=DeviceResponse, status_code=201, summary="Crear dispositivo", description="Registra un equipo con número de serie único.", response_description="Dispositivo registrado")
def create_device(payload: DeviceCreate, db: Session = Depends(get_db)):
    return service.create_device(db, payload)


@router.get("/{device_id}", response_model=DeviceResponse, summary="Consultar dispositivo", description="Obtiene un equipo por su identificador.", response_description="Datos del dispositivo")
def get_device(device_id: int, db: Session = Depends(get_db)):
    return service.get_device(db, device_id)


@router.put("/{device_id}", response_model=DeviceResponse, summary="Reemplazar dispositivo", description="Reemplaza los campos de un equipo sin préstamos abiertos.", response_description="Dispositivo actualizado")
def replace_device(device_id: int, payload: DeviceUpdate, db: Session = Depends(get_db)):
    return service.update_device(db, service.get_device(db, device_id), payload)


@router.patch("/{device_id}", response_model=DeviceResponse, summary="Modificar dispositivo", description="Actualiza solo los campos enviados de un equipo sin préstamos abiertos.", response_description="Dispositivo actualizado")
def patch_device(device_id: int, payload: DevicePatch, db: Session = Depends(get_db)):
    return service.update_device(db, service.get_device(db, device_id), payload, partial=True)


@router.delete("/{device_id}", status_code=204, summary="Eliminar dispositivo", description="Elimina un equipo únicamente si no tiene historial de préstamos.", response_description="Eliminación sin contenido")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    service.delete_device(db, service.get_device(db, device_id))
    return Response(status_code=204)


@router.get("/{device_id}/loans", response_model=list[LoanDetailResponse], summary="Historial del dispositivo", description="Consulta con joins todos los préstamos históricos de un equipo.", response_description="Préstamos con usuario y dispositivo")
def device_loans(device_id: int, db: Session = Depends(get_db)):
    service.get_device(db, device_id)
    return loan_service.list_loans(db, device_id=device_id)
