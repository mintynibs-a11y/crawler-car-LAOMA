"""
京东 (JD.com) product-review crawler.

Targets the public comment API used by JD's own website.
Endpoint: https://club.jd.com/comment/productPageComments.action
"""

import logging
from typing import List
from urllib.parse import quote

from ..models import Comment
from .base import BaseCrawler

logger = logging.getLogger(__name__)

# JD SKU IDs for popular car exterior / body-kit related product categories.
# These are used as seed products when a generic keyword search is requested.
_CAR_EXTERIOR_SKUS = [
    "100047965793",  # 汽车贴膜
    "100012716834",  # 车身改色膜
    "10053878617990", # 汽车外饰套件
]

_COMMENT_API = "https://club.jd.com/comment/productPageComments.action"

_SEARCH_API = "https://search.jd.com/Search"


class JDCrawler(BaseCrawler):
    """Crawl user reviews from JD.com for car exterior products."""

    PLATFORM = "京东"

    def _crawl(self, keyword: str) -> List[Comment]:
        comments: List[Comment] = []

        # Step 1: search for relevant products
        skus = self._search_products(keyword)
        if not skus:
            logger.warning("[JD] No products found for '%s', using default SKUs.", keyword)
            skus = _CAR_EXTERIOR_SKUS[: self.max_pages]

        # Step 2: fetch reviews for each SKU (up to max_pages SKUs)
        for sku in skus[: self.max_pages]:
            comments.extend(self._fetch_reviews(sku, keyword))
            self._sleep()

        return comments

    # ------------------------------------------------------------------

    def _search_products(self, keyword: str) -> List[str]:
        """Return a list of product SKU ids matching *keyword*."""
        try:
            params = {
                "keyword": keyword,
                "enc": "utf-8",
                "page": 1,
                "s": 1,
                "click": 0,
            }
            resp = self._get(_SEARCH_API, params=params)
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(resp.text, "lxml")
            skus = []
            for li in soup.select("li.gl-item"):
                data_sku = li.get("data-sku")
                if data_sku:
                    skus.append(str(data_sku))
            return skus[:10]
        except Exception as exc:
            logger.warning("[JD] Product search failed: %s", exc)
            return []

    def _fetch_reviews(self, sku: str, keyword: str) -> List[Comment]:
        """Fetch up to 3 pages of reviews for a single SKU."""
        comments: List[Comment] = []
        for page in range(0, 3):
            try:
                params = {
                    "productId": sku,
                    "score": 0,       # all scores
                    "sortType": 5,    # newest first
                    "page": page,
                    "pageSize": 10,
                    "isShadowSku": 0,
                    "fold": 1,
                }
                resp = self._get(_COMMENT_API, params=params)
                data = resp.json()
                items = data.get("comments", [])
                if not items:
                    break
                for item in items:
                    comments.append(
                        Comment(
                            platform=self.PLATFORM,
                            comment_id=str(item.get("id", "")),
                            content=item.get("content", ""),
                            author=item.get("nickname", ""),
                            author_id=str(item.get("guid", "")),
                            publish_time=item.get("creationTime", ""),
                            likes=int(item.get("usefulVoteCount", 0)),
                            replies=int(item.get("replyCount", 0)),
                            source_url=f"https://item.jd.com/{sku}.html",
                            source_title=item.get("productColor", ""),
                            keyword=keyword,
                            extra={
                                "score": item.get("score"),
                                "sku": sku,
                            },
                        )
                    )
                self._sleep()
            except Exception as exc:
                logger.warning("[JD] Page %d for SKU %s failed: %s", page, sku, exc)
                break
        return comments
