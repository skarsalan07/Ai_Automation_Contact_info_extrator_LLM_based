"""Top-level orchestrator. Exposes enrich_company(url) -> dict matching the strict schema."""
from __future__ import annotations

from backend.config import get_settings
from backend.schemas.company import CompanyProfile
from backend.services import extractor, llm, scraper
from backend.utils.logger import logger


def enrich_company(url: str, website_name: str | None = None) -> dict:
    """End-to-end enrichment. Always returns a dict matching CompanyProfile schema —
    never raises, never returns null fields."""
    settings = get_settings()

    safe_url = scraper.normalize_url(url)
    if not safe_url:
        logger.warning(f"invalid url: {url!r}")
        return CompanyProfile().model_dump()

    try:
        pages_to_visit, home_html = scraper.discover_pages(safe_url)
        if not pages_to_visit:
            logger.warning(f"no pages discovered for {safe_url}")
            return CompanyProfile(
                website_name=website_name or extractor.derive_website_name(safe_url),
            ).model_dump()

        pages = scraper.fetch_pages(pages_to_visit, home_html)
        combined_text, combined_html = extractor.consolidate_pages(pages)

        if not combined_text:
            logger.warning(f"empty scraped text for {safe_url}")
            return CompanyProfile(
                website_name=website_name or extractor.derive_website_name(safe_url),
            ).model_dump()

        company_name = extractor.extract_company_name(home_html or combined_html, safe_url)
        emails = extractor.extract_emails(combined_text)
        phones = extractor.extract_phones(combined_text)
        address = extractor.extract_address(combined_html, combined_text)
        primary_phone = phones[0] if phones else ""

        capped_text = extractor.cap_words(combined_text, settings.MAX_CONTEXT_WORDS)
        insights = llm.generate_insights(safe_url, company_name, capped_text)

        # anti-hallucination — drop any contact not in scraped text
        kept_mail, kept_phone, kept_addr = extractor.validate_contacts_against_source(
            profile_mail=emails,
            profile_phone=primary_phone,
            profile_address=address,
            raw_text=combined_text,
        )

        profile = CompanyProfile(
            website_name=website_name or extractor.derive_website_name(safe_url),
            company_name=company_name,
            address=kept_addr,
            mobile_number=kept_phone,
            mail=kept_mail,
            core_service=insights.get("core_service", ""),
            target_customer=insights.get("target_customer", ""),
            probable_pain_point=insights.get("probable_pain_point", ""),
            outreach_opener=insights.get("outreach_opener", ""),
        )
        return profile.model_dump()
    except Exception as e:
        logger.error(f"enrich_company failed for {safe_url}: {type(e).__name__}: {e}")
        return CompanyProfile(
            website_name=website_name or extractor.derive_website_name(safe_url),
        ).model_dump()
