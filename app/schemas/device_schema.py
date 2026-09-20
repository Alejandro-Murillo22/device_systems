from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator


class DeviceCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid", json_schema_extra={"example": {"name": "Lenovo ThinkPad", "serial_number": "LEN-001", "device_type": "laptop", "brand": "lenovo"}})
    name: str = Field(min_length=1, max_length=120)
    serial_number: str = Field(min_length=1, max_length=100)
    device_type: str = Field(min_length=1, max_length=50)
    brand: str | None = Field(default=None, max_length=80)
    is_available: bool = True


class DeviceUpdate(DeviceCreate):
    is_available: bool


class DevicePatch(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=120)
    serial_number: str | None = Field(default=None, min_length=1, max_length=100)
    device_type: str | None = Field(default=None, min_length=1, max_length=50)
    brand: str | None = Field(default=None, max_length=80)
    is_available: bool | None = None

    @model_validator(mode="after")
    def reject_nulls(self):
        for field in self.model_fields_set - {"brand"}:
            if getattr(self, field) is None:
                raise ValueError(f"{field} no puede ser null")
        return self


class DeviceResponse(DeviceCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
