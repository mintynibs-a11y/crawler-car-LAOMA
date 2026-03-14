"""
Data models for the car exterior comment crawler.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
import json


@dataclass
class Comment:
    """Represents a single user comment."""

    platform: str
    comment_id: str
    content: str
    author: str
    author_id: str
    publish_time: str
    likes: int = 0
    replies: int = 0
    source_url: str = ""
    source_title: str = ""
    keyword: str = ""
    extra: dict = field(default_factory=dict)
    crawled_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class CrawlResult:
    """Result of a crawling session for one platform."""

    platform: str
    keyword: str
    total: int
    comments: list
    success: bool = True
    error: Optional[str] = None
    crawled_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "platform": self.platform,
            "keyword": self.keyword,
            "total": self.total,
            "success": self.success,
            "error": self.error,
            "crawled_at": self.crawled_at,
            "comments": [c.to_dict() if isinstance(c, Comment) else c for c in self.comments],
        }
