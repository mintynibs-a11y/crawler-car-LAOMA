"""
Bilibili comment crawler.

Uses Bilibili's public API to fetch video comments about car exterior design.

Search API:  https://api.bilibili.com/x/web-interface/wbi/search/type  (WBI-signed)
Comment API: https://api.bilibili.com/x/v2/reply/main
Nav API:     https://api.bilibili.com/x/web-interface/nav  (WBI key source)

Bilibili requires WBI (Web Baseline Interface) request signing for the search
API since 2023.  Set the ``BILI_COOKIE`` environment variable to a valid
Bilibili session cookie string to authenticate comment fetching.
"""

import hashlib
import logging
import os
import time
from typing import List
from urllib.parse import urlencode

from ..models import Comment
from .base import BaseCrawler

logger = logging.getLogger(__name__)

_NAV_API = "https://api.bilibili.com/x/web-interface/nav"
_SEARCH_API = "https://api.bilibili.com/x/web-interface/wbi/search/type"
_COMMENT_API = "https://api.bilibili.com/x/v2/reply/main"

# Bilibili WBI key-shuffling table (reverse-engineered, stable across versions).
_MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
]


class BilibiliCrawler(BaseCrawler):
    """Crawl video comments from Bilibili for car exterior content."""

    PLATFORM = "bilibili"

    def __init__(self, cookie: str | None = None, **kwargs):
        super().__init__(**kwargs)
        cookie = cookie or os.getenv("BILI_COOKIE", "")
        headers: dict = {
            "Referer": "https://www.bilibili.com/",
            "Origin": "https://www.bilibili.com",
        }
        if cookie:
            headers["Cookie"] = cookie
        self.session.headers.update(headers)
        self._wbi_mixin_key: str | None = None

    # ------------------------------------------------------------------
    # WBI signing helpers
    # ------------------------------------------------------------------

    def _get_mixin_key(self) -> str:
        """Fetch and cache the WBI mixin key from Bilibili's nav API."""
        if self._wbi_mixin_key is not None:
            return self._wbi_mixin_key
        try:
            resp = self.session.get(_NAV_API, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            img_url: str = data["data"]["wbi_img"]["img_url"]
            sub_url: str = data["data"]["wbi_img"]["sub_url"]
            img_key = img_url.rsplit("/", 1)[-1].split(".")[0]
            sub_key = sub_url.rsplit("/", 1)[-1].split(".")[0]
            merged = img_key + sub_key
            mixin_key = "".join(merged[i] for i in _MIXIN_KEY_ENC_TAB if i < len(merged))[:32]
            self._wbi_mixin_key = mixin_key
        except Exception as exc:
            logger.warning("[Bilibili] Failed to fetch WBI mixin key: %s", exc)
            self._wbi_mixin_key = ""
        return self._wbi_mixin_key

    def _sign_wbi(self, params: dict) -> dict:
        """Return *params* augmented with WBI signature fields (``wts`` + ``w_rid``)."""
        mixin_key = self._get_mixin_key()
        if not mixin_key:
            return params
        signed = dict(params)
        signed["wts"] = int(time.time())
        # Sort and URL-encode, then strip characters that Bilibili's validator rejects.
        query = urlencode(sorted(signed.items()))
        for ch in "!'()*":
            query = query.replace(ch, "")
        signed["w_rid"] = hashlib.md5((query + mixin_key).encode()).hexdigest()
        return signed

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
            params = self._sign_wbi(
                {
                    "search_type": "video",
                    "keyword": keyword,
                    "page": 1,
                    "page_size": 10,
                }
            )
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
