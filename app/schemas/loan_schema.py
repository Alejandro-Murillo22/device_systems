from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.device_schema import DeviceResponse
from app.schemas.user_schema import UserPublic


class LoanStatus(str, Enum):
    ACTIVE = "active"
    RETURNED = "returned"
    OVERDUE = "overdue"


class LoanCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"example": {"user_id": 1, "device_id": 1}})
    user_id: int = Field(gt=0)
    device_id: int = Field(gt=0)


class LoanUpdate(BaseModel):
    """Estado y fecha controlados por el servidor al devolver."""
    status: LoanStatus
    return_date: datetime | None


class LoanResponse(LoanCreate, LoanUpdate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    loan_date: datetime


class LoanDetailResponse(LoanResponse):
    user: UserPublic
    device: DeviceResponse
