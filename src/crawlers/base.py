"""
Base crawler class providing common interface and helpers.
"""

import logging
from abc import ABC, abstractmethod
from typing import List

from ..models import Comment, CrawlResult
from ..utils import build_session, rate_limit

logger = logging.getLogger(__name__)


class BaseCrawler(ABC):
    """Abstract base for all platform crawlers."""

    PLATFORM: str = ""

    def __init__(self, max_pages: int = 5, delay: tuple = (1.0, 3.0)):
        """
        Args:
            max_pages:  Maximum number of pages/requests per keyword.
            delay:      (min_sec, max_sec) range for inter-request sleep.
        """
        self.max_pages = max_pages
        self.delay = delay
        self.session = build_session()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def crawl(self, keyword: str) -> CrawlResult:
        """Entry point: crawl *keyword* and return a CrawlResult."""
        logger.info("[%s] Starting crawl for: %s", self.PLATFORM, keyword)
        try:
            comments = self._crawl(keyword)
            return CrawlResult(
                platform=self.PLATFORM,
                keyword=keyword,
                total=len(comments),
                comments=comments,
            )
        except Exception as exc:
            logger.error("[%s] Crawl failed for '%s': %s", self.PLATFORM, keyword, exc)
            return CrawlResult(
                platform=self.PLATFORM,
                keyword=keyword,
                total=0,
                comments=[],
                success=False,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Subclass contract
    # ------------------------------------------------------------------

    @abstractmethod
    def _crawl(self, keyword: str) -> List[Comment]:
        """Implemented by each platform-specific crawler."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _sleep(self) -> None:
        rate_limit(*self.delay)

    def _get(self, url: str, **kwargs) -> "requests.Response":
        resp = self.session.get(url, timeout=15, **kwargs)
        resp.raise_for_status()
        return resp

    def _post(self, url: str, **kwargs) -> "requests.Response":
        resp = self.session.post(url, timeout=15, **kwargs)
        resp.raise_for_status()
        return resp
