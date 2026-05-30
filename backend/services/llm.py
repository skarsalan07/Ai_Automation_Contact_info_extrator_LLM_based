"""Groq llama-3.3-70b client. Strict prompt: no hallucination, return JSON only."""
from __future__ import annotations

import json
import re
from typing import Optional

from groq import Groq

from backend.config import get_settings
from backend.utils.logger import logger

SYSTEM_PROMPT = (
    "You are a B2B prospect-research analyst. "
    "You ONLY use information explicitly found in the website text the user provides. "
    "If a fact is not present, respond with the string \"Unknown\" for that field. "
    "Never guess, never fabricate, never invent companies, services, customers, or contacts. "
    "Return ONLY valid JSON matching the exact schema requested — no prose, no markdown fences."
)

USER_TEMPLATE = """Given the website text below, produce a JSON object with EXACTLY these keys:

- "core_service": one or two sentences naming the primary service/product the company sells.
- "target_customer": one sentence describing who buys from this company (industry, size, role).
- "probable_pain_point": one sentence describing the pain point this company likely solves for that customer.
- "outreach_opener": one short (1-2 sentence) cold-email opener that references something concrete from the text.

Rules:
- Use ONLY facts present in the text. If unclear, use "Unknown".
- Do NOT include emails, phone numbers, or addresses (these are extracted separately).
- Do NOT mention competitors not named in the text.
- Output a single JSON object. No markdown. No commentary.

Website URL: {url}
Website Name: {name}

--- WEBSITE TEXT START ---
{text}
--- WEBSITE TEXT END ---

JSON:"""


_client: Optional[Groq] = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        settings = get_settings()
        if not settings.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not set")
        _client = Groq(api_key=settings.GROQ_API_KEY)
    return _client


def _strip_code_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```\s*$", "", s)
    return s.strip()


def _safe_parse_json(raw: str) -> dict:
    cleaned = _strip_code_fences(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}
    return {}


def generate_insights(url: str, website_name: str, scraped_text: str) -> dict:
    """Call Groq and return a dict with the 4 insight fields. Never raises."""
    settings = get_settings()
    fields = {
        "core_service": "",
        "target_customer": "",
        "probable_pain_point": "",
        "outreach_opener": "",
    }
    if not scraped_text.strip():
        logger.warning("LLM skipped — empty scraped text")
        return fields
    try:
        client = _get_client()
    except Exception as e:
        logger.error(f"LLM client init failed: {e}")
        return fields

    user = USER_TEMPLATE.format(url=url, name=website_name or "Unknown", text=scraped_text)
    try:
        completion = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=600,
            response_format={"type": "json_object"},
        )
        raw = completion.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return fields

    parsed = _safe_parse_json(raw)
    for k in fields:
        v = parsed.get(k, "")
        if v is None:
            v = ""
        v = str(v).strip()
        if v.lower() in ("unknown", "n/a", "none", "null"):
            v = ""
        fields[k] = v
    return fields
