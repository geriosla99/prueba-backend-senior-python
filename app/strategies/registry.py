"""Maps each product to its policy.

Replaces an if/elif chain: adding a product means adding one entry here,
without touching the endpoint or the service (Open/Closed principle).
"""

from collections.abc import Mapping

from app.domain import Product
from app.strategies.base import EvaluationPolicy
from app.strategies.policies import AggressivePolicy, ConservativePolicy, StandardPolicy


class UnsupportedProductError(LookupError):
    pass


class PolicyRegistry:
    def __init__(self, policies: Mapping[Product, EvaluationPolicy]):
        self._policies = dict(policies)

    def for_product(self, product: Product) -> EvaluationPolicy:
        try:
            return self._policies[product]
        except KeyError as exc:
            raise UnsupportedProductError(f"No policy registered for {product}") from exc


def default_registry() -> PolicyRegistry:
    return PolicyRegistry(
        {
            Product.PHONE: ConservativePolicy(),
            Product.TWIST: StandardPolicy(),
            Product.CARD: AggressivePolicy(),
        }
    )
