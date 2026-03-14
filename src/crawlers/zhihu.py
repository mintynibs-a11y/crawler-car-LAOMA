"""
知乎 (Zhihu) answer/comment crawler.

Uses Zhihu's internal search and content APIs to fetch comments on
questions and articles related to car exterior design.

Search API:  https://www.zhihu.com/api/v4/search_v3
Answer API:  https://www.zhihu.com/api/v4/questions/{qid}/answers
Comment API: https://www.zhihu.com/api/v4/answers/{aid}/comments
"""

import logging
from typing import List

from ..models import Comment
from .base import BaseCrawler

logger = logging.getLogger(__name__)

_SEARCH_API = "https://www.zhihu.com/api/v4/search_v3"
_ANSWER_COMMENT_API = "https://www.zhihu.com/api/v4/answers/{answer_id}/comments"
_QUESTION_ANSWERS_API = "https://www.zhihu.com/api/v4/questions/{question_id}/answers"


class ZhihuCrawler(BaseCrawler):
    """Crawl comments/answers from Zhihu for car exterior topics."""

    PLATFORM = "知乎"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.session.headers.update(
            {
                "Referer": "https://www.zhihu.com/",
                "x-requested-with": "fetch",
            }
        )

    def _crawl(self, keyword: str) -> List[Comment]:
        comments: List[Comment] = []
        questions = self._search_questions(keyword)
        for qid, title, url in questions[: self.max_pages]:
            answers = self._fetch_answers(qid, title, url, keyword)
            comments.extend(answers)
            self._sleep()
        return comments

    # ------------------------------------------------------------------

    def _search_questions(self, keyword: str) -> List[tuple]:
        """Return list of (question_id, title, url) from a keyword search."""
        results = []
        try:
            params = {
                "t": "question",
                "q": keyword,
                "correction": 1,
                "offset": 0,
                "limit": 10,
                "lc_idx": 0,
                "show_all_topics": 0,
            }
            resp = self._get(_SEARCH_API, params=params)
            data = resp.json()
            items = data.get("data", [])
            for item in items:
                obj = item.get("object", {})
                if obj.get("type") != "question":
                    continue
                qid = str(obj.get("id", ""))
                title = obj.get("title", "")
                url = obj.get("url", f"https://www.zhihu.com/question/{qid}")
                if qid:
                    results.append((qid, title, url))
        except Exception as exc:
            logger.warning("[Zhihu] Question search failed: %s", exc)
        return results

    def _fetch_answers(self, qid: str, title: str, url: str, keyword: str) -> List[Comment]:
        """Fetch top answers for a question and treat their content as comments."""
        comments: List[Comment] = []
        try:
            params = {
                "include": "data[*].is_normal,content,voteup_count,comment_count,author",
                "offset": 0,
                "limit": 10,
                "sort_by": "default",
            }
            api_url = _QUESTION_ANSWERS_API.format(question_id=qid)
            resp = self._get(api_url, params=params)
            data = resp.json()
            answers = data.get("data", [])
            for answer in answers:
                from bs4 import BeautifulSoup

                raw_content = answer.get("content", "")
                plain_text = BeautifulSoup(raw_content, "lxml").get_text(separator=" ").strip()
                author = answer.get("author", {})
                comments.append(
                    Comment(
                        platform=self.PLATFORM,
                        comment_id=str(answer.get("id", "")),
                        content=plain_text,
                        author=author.get("name", ""),
                        author_id=str(author.get("id", "")),
                        publish_time=str(answer.get("updated_time", "")),
                        likes=int(answer.get("voteup_count", 0)),
                        replies=int(answer.get("comment_count", 0)),
                        source_url=url,
                        source_title=title,
                        keyword=keyword,
                        extra={"question_id": qid},
                    )
                )
        except Exception as exc:
            logger.warning("[Zhihu] Answer fetch failed for question %s: %s", qid, exc)
        return comments
