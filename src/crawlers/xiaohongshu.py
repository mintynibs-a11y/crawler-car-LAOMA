"""
小红书 (Xiaohongshu / RedNote) note comment crawler.

小红书 uses a private API that requires signed headers. This module
implements a best-effort approach using the publicly observable API
endpoints combined with a session cookie that the user can supply via
the environment variable ``XHS_COOKIE``.

Required env var (optional but strongly recommended):
    XHS_COOKIE  – the full Cookie header value from a logged-in browser session.

Search API:   https://edith.xiaohongshu.com/api/sns/web/v1/search/notes
Comment API:  https://edith.xiaohongshu.com/api/sns/web/v2/comment/page
"""

import hashlib
import logging
import os
import time
from typing import List

from ..models import Comment
from .base import BaseCrawler

logger = logging.getLogger(__name__)

_SEARCH_API = "https://edith.xiaohongshu.com/api/sns/web/v1/search/notes"
_COMMENT_API = "https://edith.xiaohongshu.com/api/sns/web/v2/comment/page"
_NOTE_BASE_URL = "https://www.xiaohongshu.com/explore/{note_id}"


def _xhs_sign(uri: str, data: str | None, a1: str = "") -> dict:
    """Minimal placeholder for XHS request signing.

    A proper implementation requires JavaScript execution or reverse-engineered
    native code. Here we produce a structure that lets the session proceed when
    a valid cookie is provided (the cookie itself carries auth state).
    """
    ts = str(int(time.time() * 1000))
    return {
        "x-s": hashlib.md5((uri + ts + a1).encode()).hexdigest(),
        "x-t": ts,
    }


class XiaohongshuCrawler(BaseCrawler):
    """Crawl note comments from Xiaohongshu for car exterior topics."""

    PLATFORM = "小红书"

    def __init__(self, cookie: str | None = None, **kwargs):
        super().__init__(**kwargs)
        cookie = cookie or os.getenv("XHS_COOKIE", "")
        if not cookie:
            logger.warning(
                "[XHS] XHS_COOKIE not set – API calls will return no data. "
                "Set the XHS_COOKIE environment variable with a valid cookie "
                "from a logged-in browser session on xiaohongshu.com."
            )
        self.session.headers.update(
            {
                "Referer": "https://www.xiaohongshu.com/",
                "Origin": "https://www.xiaohongshu.com",
                "Cookie": cookie,
                "Content-Type": "application/json;charset=UTF-8",
            }
        )

    def _crawl(self, keyword: str) -> List[Comment]:
        comments: List[Comment] = []
        notes = self._search_notes(keyword)
        for note_id, title, url in notes[: self.max_pages]:
            comments.extend(self._fetch_comments(note_id, title, url, keyword))
            self._sleep()
        return comments

    # ------------------------------------------------------------------

    def _search_notes(self, keyword: str) -> List[tuple]:
        """Return list of (note_id, title, url) for *keyword*."""
        results = []
        try:
            payload = {
                "keyword": keyword,
                "page": 1,
                "page_size": 20,
                "search_id": "",
                "sort": "general",
                "note_type": 0,
            }
            sign = _xhs_sign("/api/sns/web/v1/search/notes", str(payload))
            self.session.headers.update(sign)
            resp = self._post(_SEARCH_API, json=payload)
            data = resp.json()
            # Log API-level errors (e.g. auth failures) to help with diagnosis.
            if not data.get("success", True) or data.get("code", 0) != 0:
                logger.warning(
                    "[XHS] Search API returned error for '%s': code=%s msg=%s – "
                    "check that XHS_COOKIE is valid.",
                    keyword,
                    data.get("code"),
                    data.get("msg", data.get("message", "")),
                )
                return results
            items = data.get("data", {}).get("items", [])
            for item in items:
                note = item.get("note_card", item)
                note_id = note.get("id", item.get("id", ""))
                display_title = note.get("display_title", note.get("title", ""))
                url = _NOTE_BASE_URL.format(note_id=note_id)
                if note_id:
                    results.append((note_id, display_title, url))
        except Exception as exc:
            logger.warning("[XHS] Note search failed: %s", exc)
        return results

    def _fetch_comments(self, note_id: str, title: str, url: str, keyword: str) -> List[Comment]:
        """Fetch comments for a single note."""
        comments: List[Comment] = []
        cursor = ""
        for _ in range(3):
            try:
                params = {
                    "note_id": note_id,
                    "cursor": cursor,
                    "top_comment_id": "",
                    "image_formats": "jpg,webp,avif",
                }
                sign = _xhs_sign("/api/sns/web/v2/comment/page", None)
                self.session.headers.update(sign)
                resp = self._get(_COMMENT_API, params=params)
                data = resp.json()
                # Log API-level errors to assist diagnosis.
                if not data.get("success", True) or data.get("code", 0) != 0:
                    logger.warning(
                        "[XHS] Comment API error for note %s: code=%s msg=%s",
                        note_id,
                        data.get("code"),
                        data.get("msg", data.get("message", "")),
                    )
                    break
                comment_list = data.get("data", {}).get("comments", [])
                if not comment_list:
                    break
                for c in comment_list:
                    user = c.get("user_info", {})
                    comments.append(
                        Comment(
                            platform=self.PLATFORM,
                            comment_id=str(c.get("id", "")),
                            content=c.get("content", ""),
                            author=user.get("nickname", ""),
                            author_id=str(user.get("user_id", "")),
                            publish_time=str(c.get("create_time", "")),
                            likes=int(c.get("like_count", 0)),
                            replies=int(len(c.get("sub_comments", []))),
                            source_url=url,
                            source_title=title,
                            keyword=keyword,
                            extra={"note_id": note_id},
                        )
                    )
                cursor = data.get("data", {}).get("cursor", "")
                if not cursor or not data.get("data", {}).get("has_more"):
                    break
                self._sleep()
            except Exception as exc:
                logger.warning("[XHS] Comment fetch failed for note %s: %s", note_id, exc)
                break
        return comments
