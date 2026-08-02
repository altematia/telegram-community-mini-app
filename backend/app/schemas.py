from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ApplicationCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    occupation: str = Field(min_length=2, max_length=160)
    monthly_income: int = Field(gt=0, le=10_000_000_000)
    city: str = Field(min_length=1, max_length=120)

    @field_validator("first_name", "last_name", "occupation", "city", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object:
        if isinstance(value, str):
            return " ".join(value.split())
        return value


class ApplicationCreated(BaseModel):
    id: UUID
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HealthResponse(BaseModel):
    status: str
    database: str
