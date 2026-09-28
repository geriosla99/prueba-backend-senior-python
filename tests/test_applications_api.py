"""End-to-end tests through the HTTP API with an isolated database."""

from app.dependencies import get_policy_registry
from app.domain import Product
from app.main import app
from app.strategies import ConservativePolicy, PolicyRegistry, default_registry

PHONE_OK = {
    "amount": 1_200_000,
    "monthly_income": 2_000_000,
    "employment_months": 24,
    "external_score": 750,
    "product": "PHONE",
}


def test_create_approved_application_and_fetch_it(client):
    response = client.post("/applications", json=PHONE_OK)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "APPROVED"
    assert body["rejection_reasons"] == []
    assert body["policy"] == "CONSERVATIVE"
    assert body["product"] == "PHONE"

    fetched = client.get(f"/applications/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body


def test_create_rejected_application_persists_reasons(client):
    payload = {**PHONE_OK, "external_score": 650}
    body = client.post("/applications", json=payload).json()
    assert body["status"] == "REJECTED"
    assert body["rejection_reasons"] == ["external_score below 700"]

    fetched = client.get(f"/applications/{body['id']}").json()
    assert fetched["rejection_reasons"] == ["external_score below 700"]


def test_get_unknown_application_returns_404(client):
    assert client.get("/applications/9999").status_code == 404


def test_list_with_filters(client):
    client.post("/applications", json=PHONE_OK)  # PHONE approved
    client.post("/applications", json={**PHONE_OK, "external_score": 100})  # PHONE rejected
    client.post("/applications", json={**PHONE_OK, "product": "TWIST"})  # TWIST approved
    client.post(
        "/applications", json={**PHONE_OK, "product": "TWIST", "external_score": 100}
    )  # TWIST rejected

    assert len(client.get("/applications").json()) == 4

    approved_twist = client.get("/applications", params={"status": "APPROVED", "product": "TWIST"})
    assert approved_twist.status_code == 200
    items = approved_twist.json()
    assert len(items) == 1
    assert items[0]["product"] == "TWIST"
    assert items[0]["status"] == "APPROVED"

    assert len(client.get("/applications", params={"status": "REJECTED"}).json()) == 2
    assert len(client.get("/applications", params={"product": "PHONE"}).json()) == 2


def test_invalid_filter_value_returns_422(client):
    assert client.get("/applications", params={"status": "MAYBE"}).status_code == 422


def test_validation_errors(client):
    assert client.post("/applications", json={**PHONE_OK, "product": "LOAN"}).status_code == 422
    assert client.post("/applications", json={**PHONE_OK, "external_score": 1001}).status_code == 422
    assert client.post("/applications", json={**PHONE_OK, "amount": 0}).status_code == 422
    missing = {k: v for k, v in PHONE_OK.items() if k != "monthly_income"}
    assert client.post("/applications", json=missing).status_code == 422


def test_reevaluate_uses_current_policy(client):
    created = client.post("/applications", json=PHONE_OK).json()
    assert created["status"] == "APPROVED"

    # Simulate a threshold change: PHONE now requires score >= 800.
    current = default_registry()
    stricter = PolicyRegistry(
        {
            Product.PHONE: ConservativePolicy(min_score=800),
            Product.TWIST: current.for_product(Product.TWIST),
            Product.CARD: current.for_product(Product.CARD),
        }
    )
    app.dependency_overrides[get_policy_registry] = lambda: stricter

    response = client.post(f"/applications/{created['id']}/reevaluate")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "REJECTED"
    assert body["rejection_reasons"] == ["external_score below 800"]

    # The change is persisted.
    assert client.get(f"/applications/{created['id']}").json()["status"] == "REJECTED"


def test_reevaluate_unknown_application_returns_404(client):
    assert client.post("/applications/9999/reevaluate").status_code == 404
