"""Pydantic schemas (HTTP contract)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain import CreditRequest, Decision, Product


class HealthResponse(BaseModel):
    status: str


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: int = Field(gt=0, description="Requested amount in COP")
    monthly_income: int = Field(ge=0, description="Monthly income in COP")
    employment_months: int = Field(ge=0, description="Employment tenure in months")
    external_score: int = Field(ge=0, le=1000, description="External score (0-1000)")
    product: Product

    def to_domain(self) -> CreditRequest:
        return CreditRequest(**self.model_dump())


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: int
    monthly_income: int
    employment_months: int
    external_score: int
    product: Product
    status: Decision
    policy: str
    rejection_reasons: list[str]
    created_at: datetime
    evaluated_at: datetime
