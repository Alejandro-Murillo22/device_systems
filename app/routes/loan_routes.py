from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import EmailStr
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.schemas.loan_schema import LoanCreate, LoanResponse, LoanDetailResponse, LoanStatus
from app.services import loan_service as service
from app.dependencies.auth_dependencies import get_current_active_user, require_owner_or_staff
from app.models import User

router = APIRouter(prefix="/loans", tags=["Loans"], dependencies=[Depends(get_current_active_user)], responses={401: {"description": "JWT ausente o inválido"}, 403: {"description": "Permisos insuficientes"}, 404: {"description": "Usuario, dispositivo o préstamo inexistente"}, 409: {"description": "Equipo no disponible o préstamo ya devuelto"}})


def loan_filters(user_id: int | None = Query(None, gt=0), device_id: int | None = Query(None, gt=0), status: LoanStatus | None = None, user_email: EmailStr | None = None, device_type: str | None = Query(None, min_length=1), search: str | None = Query(None, min_length=1), date_from: datetime | None = None, date_to: datetime | None = None):
    def utc(value):
        return value.astimezone(timezone.utc).replace(tzinfo=None) if value and value.tzinfo else value
    date_from, date_to = utc(date_from), utc(date_to)
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, "date_from debe ser anterior o igual a date_to")
    return dict(user_id=user_id, device_id=device_id, status=status, user_email=user_email, device_type=device_type, search=search, date_from=date_from, date_to=date_to)


@router.get("", response_model=list[LoanDetailResponse], summary="Listar y filtrar préstamos", description="Combina usuario, dispositivo, estado, correo, tipo, búsqueda y rango de fechas UTC inclusivo.", response_description="Préstamos con sus usuarios y dispositivos")
@router.get("/details", response_model=list[LoanDetailResponse], summary="Consultar préstamos con joins", description="Relaciona loans, users y devices mediante JOIN; admite los mismos filtros que el listado.", response_description="Detalle relacionado de préstamos")
def list_loans(filters: dict = Depends(loan_filters), db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    if current_user.role not in {"admin", "support"}:
        if filters["user_id"] is not None:
            require_owner_or_staff(filters["user_id"], current_user)
        filters["user_id"] = current_user.id
    return service.list_loans(db, **filters)


@router.post("", response_model=LoanResponse, status_code=201, summary="Prestar dispositivo", description="Valida las referencias y reserva el equipo en la misma transacción del préstamo.", response_description="Préstamo creado en estado active")
def create_loan(payload: LoanCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    require_owner_or_staff(payload.user_id, current_user)
    return service.create_loan(db, payload)


@router.get("/{loan_id}", response_model=LoanDetailResponse, summary="Consultar préstamo", description="Muestra el préstamo y los datos del usuario y del equipo.", response_description="Detalle del préstamo")
def get_loan(loan_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    loan = service.get_loan(db, loan_id)
    require_owner_or_staff(loan.user_id, current_user)
    return loan


@router.patch("/{loan_id}/return", response_model=LoanResponse, summary="Devolver dispositivo", description="Marca returned, registra la fecha UTC y libera el equipo en una sola transacción.", response_description="Préstamo devuelto")
def return_loan(loan_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    require_owner_or_staff(service.get_loan(db, loan_id).user_id, current_user)
    return service.return_loan(db, loan_id)
