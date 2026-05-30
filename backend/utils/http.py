import random
import time
from typing import Optional

import cloudscraper
import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from backend.config import get_settings
from backend.utils.logger import logger

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def _headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        # NOTE: omit "br" — requests doesn't decode Brotli without the brotli package,
        # and several CDNs (Cloudflare, OpenAI) prefer br when offered, leaving us with binary garbage.
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


_session: Optional[requests.Session] = None
_scraper: Optional[cloudscraper.CloudScraper] = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
    return _session


def _get_scraper() -> cloudscraper.CloudScraper:
    global _scraper
    if _scraper is None:
        _scraper = cloudscraper.create_scraper(browser={"browser": "chrome", "platform": "windows", "mobile": False})
    return _scraper


@retry(
    reraise=True,
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    retry=retry_if_exception_type((requests.RequestException,)),
)
def _try_requests(url: str, timeout: int) -> requests.Response:
    return requests.get(url, headers=_headers(), timeout=timeout, allow_redirects=True)


@retry(
    reraise=True,
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    retry=retry_if_exception_type((requests.RequestException,)),
)
def _try_session(url: str, timeout: int) -> requests.Response:
    return _get_session().get(url, headers=_headers(), timeout=timeout, allow_redirects=True)


def _try_cloudscraper(url: str, timeout: int) -> requests.Response:
    return _get_scraper().get(url, headers=_headers(), timeout=timeout, allow_redirects=True)


def fetch(url: str, timeout: Optional[int] = None) -> Optional[str]:
    """Fetch URL using fallback chain: requests -> session -> cloudscraper.

    Returns response text or None if all strategies fail.
    """
    settings = get_settings()
    t = timeout or settings.REQUEST_TIMEOUT
    strategies = [
        ("requests", _try_requests),
        ("session", _try_session),
        ("cloudscraper", _try_cloudscraper),
    ]
    last_status = None
    for name, fn in strategies:
        try:
            resp = fn(url, t)
            last_status = resp.status_code
            if 200 <= resp.status_code < 400 and resp.text:
                logger.info(f"fetch ok | {name} | {resp.status_code} | {url}")
                return resp.text
            logger.warning(f"fetch non-2xx | {name} | {resp.status_code} | {url}")
        except Exception as e:
            logger.warning(f"fetch error | {name} | {type(e).__name__}: {e} | {url}")
        time.sleep(0.4)
    logger.error(f"fetch failed | last_status={last_status} | {url}")
    return None
