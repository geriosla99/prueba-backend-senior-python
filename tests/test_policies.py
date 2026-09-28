"""Unit tests for evaluation policies (pure logic, no DB, no HTTP)."""

import pytest

from app.domain import CreditRequest, Decision, Product
from app.strategies import (
    AggressivePolicy,
    ConservativePolicy,
    StandardPolicy,
    UnsupportedProductError,
    PolicyRegistry,
    default_registry,
)


def make_request(**overrides) -> CreditRequest:
    data = dict(
        amount=1_200_000,  # installment = 100,000
        monthly_income=2_000_000,
        employment_months=24,
        external_score=750,
        product=Product.PHONE,
    )
    data.update(overrides)
    return CreditRequest(**data)


# --- Conservative (PHONE) ---------------------------------------------------

class TestConservativePolicy:
    policy = ConservativePolicy()

    def test_approves_when_all_conditions_met(self):
        result = self.policy.evaluate(make_request())
        assert result.decision == Decision.APPROVED
        assert result.reasons == []
        assert result.policy == "CONSERVATIVE"

    def test_rejects_low_score(self):
        result = self.policy.evaluate(make_request(external_score=699))
        assert result.decision == Decision.REJECTED
        assert result.reasons == ["external_score below 700"]

    def test_rejects_short_employment(self):
        result = self.policy.evaluate(make_request(employment_months=11))
        assert result.decision == Decision.REJECTED
        assert result.reasons == ["employment_months below 12"]

    def test_rejects_high_installment(self):
        # installment = 6,000,001 / 12 > 500,000 (25% of 2,000,000)
        result = self.policy.evaluate(make_request(amount=6_000_001))
        assert result.decision == Decision.REJECTED
        assert result.reasons == ["installment exceeds 25% of monthly_income"]

    def test_installment_exactly_at_limit_is_approved(self):
        # installment = 6,000,000 / 12 = 500,000 == 25% of 2,000,000
        result = self.policy.evaluate(make_request(amount=6_000_000))
        assert result.decision == Decision.APPROVED

    def test_collects_all_rejection_reasons(self):
        result = self.policy.evaluate(
            make_request(external_score=100, employment_months=0, amount=100_000_000)
        )
        assert len(result.reasons) == 3


# --- Standard (TWIST) -------------------------------------------------------

class TestStandardPolicy:
    policy = StandardPolicy()

    def test_approves_without_employment_requirement(self):
        result = self.policy.evaluate(
            make_request(product=Product.TWIST, external_score=600, employment_months=0)
        )
        assert result.decision == Decision.APPROVED

    def test_rejects_low_score(self):
        result = self.policy.evaluate(make_request(product=Product.TWIST, external_score=599))
        assert result.decision == Decision.REJECTED
        assert result.reasons == ["external_score below 600"]

    def test_rejects_high_installment(self):
        # 35% of 2,000,000 = 700,000 -> max amount 8,400,000
        result = self.policy.evaluate(make_request(product=Product.TWIST, amount=8_400_001))
        assert result.decision == Decision.REJECTED
        assert result.reasons == ["installment exceeds 35% of monthly_income"]

    def test_installment_exactly_at_limit_is_approved(self):
        result = self.policy.evaluate(make_request(product=Product.TWIST, amount=8_400_000))
        assert result.decision == Decision.APPROVED


# --- Aggressive (CARD) ------------------------------------------------------

class TestAggressivePolicy:
    policy = AggressivePolicy()

    def test_approves_by_score(self):
        result = self.policy.evaluate(
            make_request(product=Product.CARD, external_score=550, monthly_income=0)
        )
        assert result.decision == Decision.APPROVED

    def test_approves_by_score_and_income(self):
        result = self.policy.evaluate(
            make_request(product=Product.CARD, external_score=500, monthly_income=3_000_000)
        )
        assert result.decision == Decision.APPROVED

    def test_rejects_mid_score_with_low_income(self):
        result = self.policy.evaluate(
            make_request(product=Product.CARD, external_score=520, monthly_income=2_999_999)
        )
        assert result.decision == Decision.REJECTED
        assert result.reasons == [
            "external_score below 550",
            "monthly_income below 3000000",
        ]

    def test_rejects_low_score_even_with_high_income(self):
        result = self.policy.evaluate(
            make_request(product=Product.CARD, external_score=499, monthly_income=10_000_000)
        )
        assert result.decision == Decision.REJECTED
        assert result.reasons == ["external_score below 550", "external_score below 500"]

    def test_ignores_installment_and_employment(self):
        result = self.policy.evaluate(
            make_request(
                product=Product.CARD, external_score=600, amount=10**12, employment_months=0
            )
        )
        assert result.decision == Decision.APPROVED


# --- Registry ---------------------------------------------------------------

@pytest.mark.parametrize(
    "product, expected",
    [
        (Product.PHONE, ConservativePolicy),
        (Product.TWIST, StandardPolicy),
        (Product.CARD, AggressivePolicy),
    ],
)
def test_registry_maps_product_to_policy(product, expected):
    assert isinstance(default_registry().for_product(product), expected)


def test_registry_raises_for_unregistered_product():
    with pytest.raises(UnsupportedProductError):
        PolicyRegistry({}).for_product(Product.PHONE)
