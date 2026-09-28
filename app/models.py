"""SQLAlchemy models."""

from datetime import datetime, timezone

from sqlalchemy import JSON, BigInteger, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.domain import CreditRequest, Decision, Product


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Original input
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    monthly_income: Mapped[int] = mapped_column(BigInteger, nullable=False)
    employment_months: Mapped[int] = mapped_column(Integer, nullable=False)
    external_score: Mapped[int] = mapped_column(Integer, nullable=False)
    product: Mapped[Product] = mapped_column(
        Enum(Product, native_enum=False, length=16), nullable=False, index=True
    )

    # Evaluation outcome
    status: Mapped[Decision] = mapped_column(
        Enum(Decision, native_enum=False, length=16), nullable=False, index=True
    )
    policy: Mapped[str] = mapped_column(String(32), nullable=False)
    rejection_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    def to_credit_request(self) -> CreditRequest:
        return CreditRequest(
            amount=self.amount,
            monthly_income=self.monthly_income,
            employment_months=self.employment_months,
            external_score=self.external_score,
            product=self.product,
        )
