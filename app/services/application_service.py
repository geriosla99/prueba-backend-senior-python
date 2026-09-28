from datetime import datetime, timezone

from app.domain import CreditRequest, Decision, EvaluationResult, Product
from app.models import Application
from app.repositories import ApplicationRepository
from app.strategies import PolicyRegistry


class ApplicationNotFoundError(LookupError):
    pass


class ApplicationService:
    """Orchestrates evaluation + persistence. Knows nothing about HTTP."""

    def __init__(self, repository: ApplicationRepository, policies: PolicyRegistry):
        self._repository = repository
        self._policies = policies

    def _evaluate(self, request: CreditRequest) -> EvaluationResult:
        return self._policies.for_product(request.product).evaluate(request)

    def create(self, request: CreditRequest) -> Application:
        result = self._evaluate(request)
        application = Application(
            amount=request.amount,
            monthly_income=request.monthly_income,
            employment_months=request.employment_months,
            external_score=request.external_score,
            product=request.product,
            status=result.decision,
            policy=result.policy,
            rejection_reasons=result.reasons,
        )
        return self._repository.add(application)

    def get(self, application_id: int) -> Application:
        application = self._repository.get(application_id)
        if application is None:
            raise ApplicationNotFoundError(f"Application {application_id} not found")
        return application

    def list(
        self,
        status: Decision | None = None,
        product: Product | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Application]:
        return self._repository.list(status=status, product=product, limit=limit, offset=offset)

    def reevaluate(self, application_id: int) -> Application:
        """Re-run evaluation with the *current* policy (e.g. after thresholds change)."""
        application = self.get(application_id)
        result = self._evaluate(application.to_credit_request())
        application.status = result.decision
        application.policy = result.policy
        application.rejection_reasons = result.reasons
        application.evaluated_at = datetime.now(timezone.utc)
        return self._repository.save(application)
