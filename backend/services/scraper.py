"""Multi-stage scraping pipeline.

Stage 1: Homepage fetch.
Stage 2: robots.txt detection.
Stage 3: sitemap.xml discovery.
Stage 4: Internal link extraction.
Stage 5: Fuzzy page ranking with RapidFuzz.
"""
from __future__ import annotations

import re
from typing import Iterable
from urllib.parse import urljoin, urlparse, urlunparse

import tldextract
from bs4 import BeautifulSoup
from rapidfuzz import fuzz

from backend.config import get_settings
from backend.utils.http import fetch
from backend.utils.logger import logger

PRIORITY_KEYWORDS = [
    "about", "about us", "company", "who we are",
    "services", "solutions", "products", "what we do",
    "contact", "contact us", "get in touch",
    "team", "leadership",
    "industries", "customers", "clients", "case studies",
]


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    if not parsed.netloc:
        return ""
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", "", "", ""))


def root_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, "/", "", "", ""))


def same_registered_domain(a: str, b: str) -> bool:
    ea = tldextract.extract(a)
    eb = tldextract.extract(b)
    return (ea.domain, ea.suffix) == (eb.domain, eb.suffix) and bool(ea.domain)


def parse_robots_for_sitemaps(robots_text: str) -> list[str]:
    sitemaps = []
    for line in robots_text.splitlines():
        line = line.strip()
        if line.lower().startswith("sitemap:"):
            sm = line.split(":", 1)[1].strip()
            if sm:
                sitemaps.append(sm)
    return sitemaps


def parse_sitemap(xml_text: str) -> list[str]:
    urls: list[str] = []
    if not xml_text:
        return urls
    try:
        soup = BeautifulSoup(xml_text, "lxml-xml")
    except Exception:
        soup = BeautifulSoup(xml_text, "xml")
    for loc in soup.find_all("loc"):
        u = (loc.text or "").strip()
        if u:
            urls.append(u)
    return urls


def discover_sitemap_urls(base: str) -> list[str]:
    base = root_url(base)
    candidates: list[str] = []
    robots = fetch(urljoin(base, "/robots.txt"))
    if robots:
        candidates.extend(parse_robots_for_sitemaps(robots))
    candidates.append(urljoin(base, "/sitemap.xml"))
    candidates.append(urljoin(base, "/sitemap_index.xml"))

    seen: set[str] = set()
    urls: list[str] = []
    for sm in candidates:
        if sm in seen:
            continue
        seen.add(sm)
        xml = fetch(sm)
        if not xml:
            continue
        found = parse_sitemap(xml)
        # nested sitemap indexes
        for u in found:
            if u.endswith(".xml") and u not in seen:
                seen.add(u)
                inner = fetch(u)
                if inner:
                    urls.extend(parse_sitemap(inner))
            else:
                urls.append(u)
    return urls


def extract_internal_links(html: str, base: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    out: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = (a.get("href") or "").strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(base, href)
        if not absolute.startswith(("http://", "https://")):
            continue
        if not same_registered_domain(absolute, base):
            continue
        # strip fragments/queries
        parsed = urlparse(absolute)
        cleaned = urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", "", "", ""))
        out.add(cleaned)
    return sorted(out)


def _path_signal(url: str) -> str:
    """Convert URL path into a phrase RapidFuzz can score against keywords."""
    path = urlparse(url).path.lower()
    path = re.sub(r"[-_/]+", " ", path)
    return path.strip()


def rank_urls(urls: Iterable[str], homepage: str, limit: int) -> list[str]:
    """Rank URLs by fuzzy match against priority keywords; always include homepage."""
    homepage = root_url(homepage)
    scored: dict[str, int] = {}
    for u in urls:
        if u == homepage:
            continue
        signal = _path_signal(u)
        if not signal:
            continue
        best = max((fuzz.partial_ratio(signal, kw) for kw in PRIORITY_KEYWORDS), default=0)
        # boost for exact slug matches
        for kw in ("contact", "about", "services", "team"):
            if kw in signal.split():
                best = max(best, 95)
        scored[u] = best
    ranked = sorted(scored.items(), key=lambda x: (-x[1], len(x[0])))
    top = [u for u, s in ranked if s >= 55][: max(0, limit - 1)]
    return [homepage] + top


def discover_pages(start_url: str) -> tuple[list[str], str | None]:
    """Stages 1-5. Returns (pages_to_visit, homepage_html)."""
    settings = get_settings()
    homepage = normalize_url(start_url)
    if not homepage:
        return [], None

    home_html = fetch(homepage)
    candidate_urls: set[str] = set()

    if home_html:
        candidate_urls.update(extract_internal_links(home_html, homepage))

    sitemap_urls = discover_sitemap_urls(homepage)
    for u in sitemap_urls:
        if same_registered_domain(u, homepage):
            parsed = urlparse(u)
            cleaned = urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", "", "", ""))
            candidate_urls.add(cleaned)

    logger.info(f"discovered candidates={len(candidate_urls)} sitemap={len(sitemap_urls)} | {homepage}")
    ranked = rank_urls(candidate_urls, homepage, settings.MAX_PAGES_PER_SITE)
    return ranked, home_html


def fetch_pages(urls: list[str], homepage_html: str | None) -> dict[str, str]:
    """Fetch HTML for each URL. Reuse homepage HTML if already retrieved."""
    out: dict[str, str] = {}
    for i, u in enumerate(urls):
        if i == 0 and homepage_html:
            out[u] = homepage_html
            continue
        html = fetch(u)
        if html:
            out[u] = html
    return out
