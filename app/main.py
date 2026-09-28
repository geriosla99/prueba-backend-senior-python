from fastapi import FastAPI

from app import models  # noqa: F401  (registers models on Base.metadata)
from app.database import Base, engine
from app.routers.applications import router as applications_router
from app.schemas import HealthResponse

# Simple setup: create tables on startup. In production, use Alembic.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Credit Evaluation Service")


@app.get("/health", response_model=HealthResponse)
def health():
    return {"status": "ok"}


app.include_router(applications_router)
