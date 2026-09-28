"""Dependency wiring (composition root for FastAPI)."""

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories import SqlAlchemyApplicationRepository
from app.services import ApplicationService
from app.strategies import PolicyRegistry, default_registry


@lru_cache
def get_policy_registry() -> PolicyRegistry:
    return default_registry()


def get_application_service(
    db: Session = Depends(get_db),
    policies: PolicyRegistry = Depends(get_policy_registry),
) -> ApplicationService:
    return ApplicationService(SqlAlchemyApplicationRepository(db), policies)
