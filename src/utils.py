"""
Shared utilities: request session setup, rate limiting, output helpers.
"""

import csv
import json
import logging
import random
import time
from pathlib import Path
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# Default headers that mimic a modern browser
_DEFAULT_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
]


def build_session(
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    extra_headers: Optional[dict] = None,
) -> requests.Session:
    """Create a requests Session with retry logic and sensible defaults."""
    session = requests.Session()

    retry = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    headers = dict(_DEFAULT_HEADERS)
    headers["User-Agent"] = random.choice(_USER_AGENTS)
    if extra_headers:
        headers.update(extra_headers)
    session.headers.update(headers)
    return session


def rate_limit(min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
    """Sleep a random amount to avoid triggering rate-limit bans."""
    time.sleep(random.uniform(min_seconds, max_seconds))


def save_json(data: list, filepath: str | Path) -> None:
    """Persist a list of dicts to a UTF-8 JSON file."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    logger.info("Saved %d records to %s", len(data), filepath)


def save_csv(data: list, filepath: str | Path) -> None:
    """Persist a list of dicts to a UTF-8 CSV file."""
    if not data:
        logger.warning("No data to save to %s", filepath)
        return
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(data[0].keys())
    with open(filepath, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    logger.info("Saved %d records to %s", len(data), filepath)
