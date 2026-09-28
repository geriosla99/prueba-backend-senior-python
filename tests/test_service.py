"""Service unit tests using an in-memory repository (no DB, no HTTP).

Shows the value of the ApplicationRepository abstraction: the business
orchestration is tested in isolation with a fake implementation.
"""

import pytest

from app.domain import CreditRequest, Decision, Product
from app.models import Application
from app.repositories import ApplicationRepository
from app.services import ApplicationNotFoundError, ApplicationService
from app.strategies import (
    AggressivePolicy,
    ConservativePolicy,
    PolicyRegistry,
    StandardPolicy,
    default_registry,
)


class InMemoryApplicationRepository(ApplicationRepository):
    def __init__(self):
        self._items: dict[int, Application] = {}

    def add(self, application: Application) -> Application:
        application.id = len(self._items) + 1
        self._items[application.id] = application
        return application

    def save(self, application: Application) -> Application:
        self._items[application.id] = application
        return application

    def get(self, application_id: int) -> Application | None:
        return self._items.get(application_id)

    def list(self, status=None, product=None, limit=100, offset=0) -> list[Application]:
        items = [
            a
            for a in self._items.values()
            if (status is None or a.status == status)
            and (product is None or a.product == product)
        ]
        return items[offset : offset + limit]


def phone_request(**overrides) -> CreditRequest:
    data = dict(
        amount=1_200_000,
        monthly_income=2_000_000,
        employment_months=24,
        external_score=750,
        product=Product.PHONE,
    )
    data.update(overrides)
    return CreditRequest(**data)


@pytest.fixture
def repo():
    return InMemoryApplicationRepository()


def test_create_persists_decision_and_policy(repo):
    service = ApplicationService(repo, default_registry())
    created = service.create(phone_request(external_score=100))

    stored = repo.get(created.id)
    assert stored.status == Decision.REJECTED
    assert stored.policy == "CONSERVATIVE"
    assert stored.rejection_reasons == ["external_score below 700"]


def test_service_uses_policy_selected_by_product(repo):
    service = ApplicationService(repo, default_registry())
    # Score 560 fails PHONE (700) and TWIST (600) but passes CARD (550).
    assert service.create(phone_request(external_score=560)).status == Decision.REJECTED
    card = service.create(phone_request(external_score=560, product=Product.CARD))
    assert card.status == Decision.APPROVED
    assert card.policy == "AGGRESSIVE"


def test_get_missing_raises(repo):
    service = ApplicationService(repo, default_registry())
    with pytest.raises(ApplicationNotFoundError):
        service.get(42)


def test_reevaluate_applies_new_thresholds(repo):
    created = ApplicationService(repo, default_registry()).create(phone_request())
    assert created.status == Decision.APPROVED

    stricter = PolicyRegistry(
        {
            Product.PHONE: ConservativePolicy(min_score=800),
            Product.TWIST: StandardPolicy(),
            Product.CARD: AggressivePolicy(),
        }
    )
    updated = ApplicationService(repo, stricter).reevaluate(created.id)
    assert updated.status == Decision.REJECTED
    assert updated.rejection_reasons == ["external_score below 800"]
    assert updated.evaluated_at is not None
