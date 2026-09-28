"""Concrete evaluation policies.

Thresholds live on each policy instance (not hard-coded in the logic), so
they can be tuned in one place — which is exactly what the re-evaluate
endpoint is meant to support.
"""

from dataclasses import dataclass

from app.domain import CreditRequest
from app.strategies.base import EvaluationPolicy, installment_within_ratio


@dataclass(frozen=True)
class ConservativePolicy(EvaluationPolicy):
    """PHONE: score >= 700 AND employment >= 12 months AND installment <= 25% income."""

    name = "CONSERVATIVE"
    min_score: int = 700
    min_employment_months: int = 12
    max_installment_ratio_pct: int = 25

    def rejection_reasons(self, request: CreditRequest) -> list[str]:
        reasons: list[str] = []
        if request.external_score < self.min_score:
            reasons.append(f"external_score below {self.min_score}")
        if request.employment_months < self.min_employment_months:
            reasons.append(f"employment_months below {self.min_employment_months}")
        if not installment_within_ratio(
            request.amount, request.monthly_income, self.max_installment_ratio_pct
        ):
            reasons.append(
                f"installment exceeds {self.max_installment_ratio_pct}% of monthly_income"
            )
        return reasons


@dataclass(frozen=True)
class StandardPolicy(EvaluationPolicy):
    """TWIST: score >= 600 AND installment <= 35% income."""

    name = "STANDARD"
    min_score: int = 600
    max_installment_ratio_pct: int = 35

    def rejection_reasons(self, request: CreditRequest) -> list[str]:
        reasons: list[str] = []
        if request.external_score < self.min_score:
            reasons.append(f"external_score below {self.min_score}")
        if not installment_within_ratio(
            request.amount, request.monthly_income, self.max_installment_ratio_pct
        ):
            reasons.append(
                f"installment exceeds {self.max_installment_ratio_pct}% of monthly_income"
            )
        return reasons


@dataclass(frozen=True)
class AggressivePolicy(EvaluationPolicy):
    """CARD: score >= 550 OR (score >= 500 AND income >= 3,000,000)."""

    name = "AGGRESSIVE"
    min_score: int = 550
    min_score_with_income: int = 500
    min_income: int = 3_000_000

    def rejection_reasons(self, request: CreditRequest) -> list[str]:
        if request.external_score >= self.min_score:
            return []

        # Primary path failed; check the income-backed alternative path.
        alternative_failures: list[str] = []
        if request.external_score < self.min_score_with_income:
            alternative_failures.append(f"external_score below {self.min_score_with_income}")
        if request.monthly_income < self.min_income:
            alternative_failures.append(f"monthly_income below {self.min_income}")

        if not alternative_failures:
            return []
        return [f"external_score below {self.min_score}", *alternative_failures]
