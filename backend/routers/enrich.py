from fastapi import APIRouter, HTTPException

from backend.database.db import store
from backend.schemas.company import CompanyProfile, EnrichRequest
from backend.services.pipeline import enrich_company
from backend.utils.logger import logger

router = APIRouter(prefix="", tags=["enrich"])


@router.post("/enrich", response_model=CompanyProfile)
def enrich(req: EnrichRequest) -> CompanyProfile:
    try:
        result = enrich_company(req.url, website_name=req.website_name)
        profile = CompanyProfile(**result)
        row = store.add(profile.model_dump(), source_url=req.url)
        logger.info(f"persisted enrichment id={row.id} url={req.url}")
        return profile
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"/enrich failed: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Enrichment pipeline failed") from e
