"""HTML cleaning + contact / company-name extraction.

Pure extraction logic — never invents data. Contacts MUST originate from scraped text.
"""
from __future__ import annotations

import json
import re
from urllib.parse import urlparse

import tldextract
from bs4 import BeautifulSoup

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
# Phone: allows international with +, parens, dashes, spaces, and dots. 7-20 digit cluster.
PHONE_RE = re.compile(
    r"(?:(?:\+?\d{1,3}[\s\-.]?)?(?:\(?\d{2,4}\)?[\s\-.]?)?\d{3,4}[\s\-.]?\d{3,4}(?:[\s\-.]?\d{1,4})?)"
)
# Filter out tiny / nonsense numeric matches
DIGITS_RE = re.compile(r"\d")

# Heuristic address detector: tight street keywords only. Common words like
# "building" / "park" / "tower" / "unit" / "block" cause false positives in marketing copy.
ADDRESS_HINT = re.compile(
    r"\b(?:street|st\.|road|rd\.|avenue|ave\.|boulevard|blvd\.|highway|hwy|"
    r"lane|ln\.|drive|dr\.|suite|ste\.|po\sbox)\b",
    re.IGNORECASE,
)
POSTAL_HINT = re.compile(r"\b\d{4,6}(?:[-\s]\d{3,4})?\b")


def clean_html_to_text(html: str) -> str:
    """Strip scripts/styles/nav/footer/boilerplate and return condensed text."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "form", "button"]):
        tag.decompose()
    # remove obvious nav/footer/aside chrome but keep <footer> raw for address mining via separate path
    for selector in ["nav", "aside"]:
        for tag in soup.select(selector):
            tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    seen: set[str] = set()
    deduped: list[str] = []
    for ln in lines:
        key = ln.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ln)
    return "\n".join(deduped)


def cap_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


def extract_emails(text: str) -> list[str]:
    raw = EMAIL_RE.findall(text or "")
    out: list[str] = []
    seen: set[str] = set()
    for e in raw:
        e = e.strip().rstrip(".").lower()
        if e in seen:
            continue
        # filter common asset / placeholder domains
        if any(bad in e for bad in ("example.com", "yourdomain", "domain.com", "sentry.io", "wixpress.com")):
            continue
        if e.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")):
            continue
        seen.add(e)
        out.append(e)
    return out


def _normalize_phone_candidate(s: str) -> str:
    return re.sub(r"[^\d+]", "", s)


def extract_phones(text: str) -> list[str]:
    raw = PHONE_RE.findall(text or "")
    out: list[str] = []
    seen: set[str] = set()
    for cand in raw:
        digits = _normalize_phone_candidate(cand)
        if len(digits) < 10 or len(digits) > 16:
            continue
        # avoid years / dates being captured
        if re.fullmatch(r"\d{4}", digits):
            continue
        # reject unbalanced parens (regex sometimes captures "91) 9812647081")
        if cand.count("(") != cand.count(")"):
            continue
        if digits in seen:
            continue
        seen.add(digits)
        out.append(cand.strip())
    return out


def extract_structured_data(html: str) -> list[dict]:
    """Return list of JSON-LD objects from <script type=application/ld+json>."""
    out: list[dict] = []
    if not html:
        return out
    soup = BeautifulSoup(html, "lxml")
    for s in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = s.string or s.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            try:
                data = json.loads(re.sub(r",\s*([}\]])", r"\1", raw))
            except Exception:
                continue
        if isinstance(data, list):
            out.extend(d for d in data if isinstance(d, dict))
        elif isinstance(data, dict):
            graph = data.get("@graph")
            if isinstance(graph, list):
                out.extend(d for d in graph if isinstance(d, dict))
            else:
                out.append(data)
    return out


def _walk_postal(obj) -> str | None:
    if isinstance(obj, dict):
        t = obj.get("@type") or obj.get("type")
        if isinstance(t, str) and t.lower() == "postaladdress":
            parts = [
                obj.get("streetAddress"),
                obj.get("addressLocality"),
                obj.get("addressRegion"),
                obj.get("postalCode"),
                obj.get("addressCountry"),
            ]
            joined = ", ".join(str(p) for p in parts if p)
            if joined:
                return joined
        for v in obj.values():
            r = _walk_postal(v)
            if r:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _walk_postal(v)
            if r:
                return r
    return None


def extract_address(html: str, text: str) -> str:
    # 1) structured data
    for blob in extract_structured_data(html):
        addr = _walk_postal(blob)
        if addr:
            return addr
    # 2) <address> tag
    soup = BeautifulSoup(html or "", "lxml")
    for a in soup.find_all("address"):
        line = " ".join((a.get_text(" ") or "").split())
        if line and (ADDRESS_HINT.search(line) or POSTAL_HINT.search(line)):
            return line
    # 3) text-line fallback — require BOTH a street keyword AND digits AND a comma
    #    (filters out marketing sentences that happen to mention street-like words).
    candidates: list[str] = []
    for line in (text or "").splitlines():
        if not (12 <= len(line) <= 200):
            continue
        if not ADDRESS_HINT.search(line):
            continue
        if not POSTAL_HINT.search(line) and not re.search(r"\b\d{1,5}\s+\w+", line):
            continue
        if line.count(",") < 1:
            continue
        candidates.append(line.strip())
    if candidates:
        candidates.sort(key=lambda l: (-l.count(","), -len(l)))
        return candidates[0]
    return ""


def extract_company_name(html: str, url: str) -> str:
    soup = BeautifulSoup(html or "", "lxml")
    # 1) OpenGraph site_name
    og = soup.find("meta", attrs={"property": "og:site_name"})
    if og and og.get("content"):
        return og["content"].strip()
    # 2) JSON-LD Organization
    for blob in extract_structured_data(html):
        t = blob.get("@type") or blob.get("type")
        if isinstance(t, list):
            t = next((x for x in t if isinstance(x, str)), "")
        if isinstance(t, str) and t.lower() in ("organization", "corporation", "localbusiness"):
            name = blob.get("name") or blob.get("legalName")
            if name:
                return str(name).strip()
    # 3) og:title / title minus suffix
    og_title = soup.find("meta", attrs={"property": "og:title"})
    title = (og_title.get("content").strip() if og_title and og_title.get("content") else "")
    if not title and soup.title and soup.title.string:
        title = soup.title.string.strip()
    if title:
        for sep in ("|", "—", "–", " - ", " :: "):
            if sep in title:
                title = title.split(sep)[0].strip()
                break
        if title:
            return title
    # 4) logo alt
    for img in soup.find_all("img"):
        alt = (img.get("alt") or "").strip()
        if alt and "logo" in alt.lower():
            cleaned = re.sub(r"(?i)\blogo\b", "", alt).strip(" -|")
            if cleaned:
                return cleaned
    # 5) domain fallback
    ext = tldextract.extract(url or "")
    if ext.domain:
        return ext.domain.replace("-", " ").title()
    return ""


def derive_website_name(url: str) -> str:
    ext = tldextract.extract(url or "")
    if ext.domain and ext.suffix:
        return f"{ext.domain}.{ext.suffix}"
    parsed = urlparse(url or "")
    return parsed.netloc or ""


def extract_seo_text(html: str) -> str:
    """SEO metadata fallback (title / meta description / og:* / h1-h3).
    Critical for JS-rendered SPAs where body text is sparse but SEO tags are rich."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    parts: list[str] = []
    if soup.title and soup.title.string:
        parts.append(f"Title: {soup.title.string.strip()}")
    meta_targets = [
        ("name", "description"),
        ("name", "keywords"),
        ("property", "og:title"),
        ("property", "og:description"),
        ("property", "og:site_name"),
        ("name", "twitter:title"),
        ("name", "twitter:description"),
    ]
    for attr, val in meta_targets:
        tag = soup.find("meta", attrs={attr: val})
        if tag and tag.get("content"):
            parts.append(f"{val}: {tag['content'].strip()}")
    for level in ("h1", "h2", "h3"):
        for h in soup.find_all(level):
            t = h.get_text(" ", strip=True)
            if t and 3 < len(t) < 240:
                parts.append(t)
    seen: set[str] = set()
    deduped: list[str] = []
    for p in parts:
        k = p.lower()
        if k in seen:
            continue
        seen.add(k)
        deduped.append(p)
    return "\n".join(deduped)


def consolidate_pages(pages: dict[str, str]) -> tuple[str, str]:
    """Return (combined_clean_text, combined_html) across all pages.
    Merges body text + SEO metadata so SPAs still produce useful LLM context."""
    text_parts: list[str] = []
    html_parts: list[str] = []
    for url, html in pages.items():
        if not html:
            continue
        html_parts.append(html)
        body = clean_html_to_text(html)
        seo = extract_seo_text(html)
        merged = f"{seo}\n{body}" if seo else body
        text_parts.append(f"\n--- {url} ---\n{merged}")
    return ("\n".join(text_parts).strip(), "\n".join(html_parts))


def validate_contacts_against_source(profile_mail: list[str], profile_phone: str, profile_address: str, raw_text: str) -> tuple[list[str], str, str]:
    """Anti-hallucination guard: drop any contact not present verbatim in scraped text."""
    lower = (raw_text or "").lower()
    digits_only = re.sub(r"\D", "", lower)

    kept_mail = [m for m in profile_mail if m.lower() in lower]

    phone_ok = ""
    if profile_phone:
        cand_digits = re.sub(r"\D", "", profile_phone)
        if cand_digits and cand_digits in digits_only:
            phone_ok = profile_phone

    addr_ok = ""
    if profile_address:
        # accept if at least 60% of address tokens appear in source
        tokens = [t for t in re.split(r"[\s,]+", profile_address.lower()) if len(t) > 2]
        if tokens:
            hits = sum(1 for t in tokens if t in lower)
            if hits / len(tokens) >= 0.6:
                addr_ok = profile_address

    return kept_mail, phone_ok, addr_ok
