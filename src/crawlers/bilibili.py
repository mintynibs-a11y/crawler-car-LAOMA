"""
Bilibili comment crawler.

Uses Bilibili's public API to fetch video comments about car exterior design.

Search API:  https://api.bilibili.com/x/web-interface/search/type
Comment API: https://api.bilibili.com/x/v2/reply/main
"""

import logging
from typing import List

from ..models import Comment
from .base import BaseCrawler

logger = logging.getLogger(__name__)

_SEARCH_API = "https://api.bilibili.com/x/web-interface/search/type"
_COMMENT_API = "https://api.bilibili.com/x/v2/reply/main"

# wbi-signed search is required for newer endpoints; fall back to legacy.
_SEARCH_LEGACY = "https://api.bilibili.com/x/web-interface/search/type"


class BilibiliCrawler(BaseCrawler):
    """Crawl video comments from Bilibili for car exterior content."""

    PLATFORM = "bilibili"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.session.headers.update(
            {
                "Referer": "https://www.bilibili.com/",
                "Origin": "https://www.bilibili.com",
            }
        )

    def _crawl(self, keyword: str) -> List[Comment]:
        comments: List[Comment] = []
        video_ids = self._search_videos(keyword)
        for aid, title, url in video_ids[: self.max_pages]:
            comments.extend(self._fetch_comments(aid, title, url, keyword))
            self._sleep()
        return comments

    # ------------------------------------------------------------------

    def _search_videos(self, keyword: str) -> List[tuple]:
        """Return list of (aid, title, url) tuples from a keyword search."""
        results = []
        try:
            params = {
                "search_type": "video",
                "keyword": keyword,
                "page": 1,
                "page_size": 10,
            }
            resp = self._get(_SEARCH_API, params=params)
            data = resp.json()
            items = data.get("data", {}).get("result", [])
            for item in items:
                aid = str(item.get("aid", ""))
                bvid = item.get("bvid", "")
                title = item.get("title", "").replace("<em class=\"keyword\">", "").replace("</em>", "")
                url = f"https://www.bilibili.com/video/{bvid}" if bvid else f"https://www.bilibili.com/video/av{aid}"
                if aid:
                    results.append((aid, title, url))
        except Exception as exc:
            logger.warning("[Bilibili] Video search failed: %s", exc)
        return results

    def _fetch_comments(self, aid: str, title: str, url: str, keyword: str) -> List[Comment]:
        """Fetch comments for a single video by its AV id."""
        comments: List[Comment] = []
        for page in range(1, 4):
            try:
                params = {
                    "oid": aid,
                    "type": 1,   # video comments
                    "sort": 0,   # top comments first
                    "ps": 20,    # page size
                    "pn": page,
                }
                resp = self._get(_COMMENT_API, params=params)
                data = resp.json()
                replies = data.get("data", {}).get("replies") or []
                if not replies:
                    break
                for reply in replies:
                    member = reply.get("member", {})
                    comments.append(
                        Comment(
                            platform=self.PLATFORM,
                            comment_id=str(reply.get("rpid", "")),
                            content=reply.get("content", {}).get("message", ""),
                            author=member.get("uname", ""),
                            author_id=str(member.get("mid", "")),
                            publish_time=str(reply.get("ctime", "")),
                            likes=int(reply.get("like", 0)),
                            replies=int(reply.get("rcount", 0)),
                            source_url=url,
                            source_title=title,
                            keyword=keyword,
                            extra={"aid": aid},
                        )
                    )
                self._sleep()
            except Exception as exc:
                logger.warning("[Bilibili] Comment page %d for aid %s failed: %s", page, aid, exc)
                break
        return comments
