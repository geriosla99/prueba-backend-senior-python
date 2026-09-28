from abc import ABC, abstractmethod

from app.domain import Decision, Product
from app.models import Application


class ApplicationRepository(ABC):
    """Port (interface) for application persistence.

    The service depends on this abstraction, not on SQLAlchemy (Dependency
    Inversion). Swapping the storage (Postgres, an in-memory fake for tests,
    an external API...) means writing a new implementation, not touching the
    business logic.
    """

    @abstractmethod
    def add(self, application: Application) -> Application: ...

    @abstractmethod
    def save(self, application: Application) -> Application: ...

    @abstractmethod
    def get(self, application_id: int) -> Application | None: ...

    @abstractmethod
    def list(
        self,
        status: Decision | None = None,
        product: Product | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Application]: ...
