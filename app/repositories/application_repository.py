from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import Decision, Product
from app.models import Application
from app.repositories.base import ApplicationRepository


class SqlAlchemyApplicationRepository(ApplicationRepository):
    """SQLAlchemy implementation. The only class that talks to the database."""

    def __init__(self, session: Session):
        self._session = session

    def add(self, application: Application) -> Application:
        self._session.add(application)
        self._session.commit()
        self._session.refresh(application)
        return application

    def save(self, application: Application) -> Application:
        self._session.commit()
        self._session.refresh(application)
        return application

    def get(self, application_id: int) -> Application | None:
        return self._session.get(Application, application_id)

    def list(
        self,
        status: Decision | None = None,
        product: Product | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Application]:
        stmt = select(Application)
        if status is not None:
            stmt = stmt.where(Application.status == status)
        if product is not None:
            stmt = stmt.where(Application.product == product)
        stmt = stmt.order_by(Application.id).limit(limit).offset(offset)
        return list(self._session.scalars(stmt))
