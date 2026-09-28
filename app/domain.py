"""Domain types shared across layers (no framework dependencies)."""

from dataclasses import dataclass, field
from enum import Enum


class Product(str, Enum):
    PHONE = "PHONE"
    TWIST = "TWIST"
    CARD = "CARD"


class Decision(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# Fixed term assumed by the business rules: installment = amount / 12
TERM_MONTHS = 12


@dataclass(frozen=True)
class CreditRequest:
    """Input needed to evaluate a credit application."""

    amount: int
    monthly_income: int
    employment_months: int
    external_score: int
    product: Product


@dataclass(frozen=True)
class EvaluationResult:
    decision: Decision
    policy: str
    reasons: list[str] = field(default_factory=list)

    @classmethod
    def from_reasons(cls, policy: str, reasons: list[str]) -> "EvaluationResult":
        decision = Decision.REJECTED if reasons else Decision.APPROVED
        return cls(decision=decision, policy=policy, reasons=reasons)
