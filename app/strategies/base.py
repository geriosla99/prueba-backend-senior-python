from abc import ABC, abstractmethod
from typing import ClassVar

from app.domain import TERM_MONTHS, CreditRequest, EvaluationResult


class EvaluationPolicy(ABC):
    """Base class for every credit policy (Strategy + Template Method).

    `evaluate` is the fixed algorithm shared by all policies: collect the
    rejection reasons and turn them into a decision. Each concrete policy only
    implements *which* rules fail (`rejection_reasons`). This guarantees every
    policy decides the same way (no reasons -> APPROVED) and can't forget to
    set its name or build the result differently.
    """

    name: ClassVar[str]

    def evaluate(self, request: CreditRequest) -> EvaluationResult:
        reasons = self.rejection_reasons(request)
        return EvaluationResult.from_reasons(self.name, reasons)

    @abstractmethod
    def rejection_reasons(self, request: CreditRequest) -> list[str]:
        """Return every rule the request fails. Empty list means approved."""


def installment_within_ratio(amount: int, monthly_income: int, max_ratio_pct: int) -> bool:
    """True if amount / TERM_MONTHS <= max_ratio_pct% of monthly_income.

    Uses integer arithmetic (cross-multiplication) to avoid floating point
    errors at the boundary: amount * 100 <= income * pct * TERM_MONTHS.
    """
    return amount * 100 <= monthly_income * max_ratio_pct * TERM_MONTHS
