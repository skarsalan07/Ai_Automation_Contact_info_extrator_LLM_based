from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.db import Base


class CompanyResult(Base):
    __tablename__ = "company_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_url: Mapped[str] = mapped_column(String(512), index=True)
    website_name: Mapped[str] = mapped_column(String(255), default="")
    company_name: Mapped[str] = mapped_column(String(255), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    mobile_number: Mapped[str] = mapped_column(String(64), default="")
    mail: Mapped[list] = mapped_column(JSON, default=list)
    core_service: Mapped[str] = mapped_column(Text, default="")
    target_customer: Mapped[str] = mapped_column(Text, default="")
    probable_pain_point: Mapped[str] = mapped_column(Text, default="")
    outreach_opener: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
