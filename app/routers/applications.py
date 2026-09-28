from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_application_service
from app.domain import Decision, Product
from app.schemas import ApplicationCreate, ApplicationRead
from app.services import ApplicationNotFoundError, ApplicationService

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
def create_application(
    payload: ApplicationCreate,
    service: ApplicationService = Depends(get_application_service),
):
    return service.create(payload.to_domain())


@router.get("/{application_id}", response_model=ApplicationRead)
def get_application(
    application_id: int,
    service: ApplicationService = Depends(get_application_service),
):
    try:
        return service.get(application_id)
    except ApplicationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("", response_model=list[ApplicationRead])
def list_applications(
    status_filter: Decision | None = Query(default=None, alias="status"),
    product: Product | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: ApplicationService = Depends(get_application_service),
):
    return service.list(status=status_filter, product=product, limit=limit, offset=offset)


@router.post("/{application_id}/reevaluate", response_model=ApplicationRead)
def reevaluate_application(
    application_id: int,
    service: ApplicationService = Depends(get_application_service),
):
    try:
        return service.reevaluate(application_id)
    except ApplicationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
