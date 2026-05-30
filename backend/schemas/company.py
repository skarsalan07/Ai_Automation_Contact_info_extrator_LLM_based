from datetime import datetime
from typing import List

from pydantic import BaseModel, Field, field_validator


class EnrichRequest(BaseModel):
    url: str = Field(..., min_length=3, description="Company website URL")
    website_name: str | None = Field(default=None, description="Optional friendly name")


class CompanyProfile(BaseModel):
    """Strict output schema — every field is always present, never null."""

    website_name: str = ""
    company_name: str = ""
    address: str = ""
    mobile_number: str = ""
    mail: List[str] = Field(default_factory=list)
    core_service: str = ""
    target_customer: str = ""
    probable_pain_point: str = ""
    outreach_opener: str = ""

    @field_validator(
        "website_name",
        "company_name",
        "address",
        "mobile_number",
        "core_service",
        "target_customer",
        "probable_pain_point",
        "outreach_opener",
        mode="before",
    )
    @classmethod
    def coerce_none_to_empty_string(cls, v):
        if v is None:
            return ""
        return str(v).strip()

    @field_validator("mail", mode="before")
    @classmethod
    def coerce_mail(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        if isinstance(v, list):
            return [str(x).strip() for x in v if x is not None and str(x).strip()]
        return []


class CompanyProfileStored(CompanyProfile):
    id: int
    source_url: str
    created_at: datetime
