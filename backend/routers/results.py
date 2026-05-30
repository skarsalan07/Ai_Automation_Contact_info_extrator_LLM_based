from fastapi import APIRouter, Query

from backend.database.db import store
from backend.schemas.company import CompanyProfileStored

router = APIRouter(prefix="", tags=["results"])


@router.get("/results", response_model=list[CompanyProfileStored])
def list_results(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[CompanyProfileStored]:
    return store.list(limit=limit, offset=offset)
