"""
Tests for data models.
"""

import json
from src.models import Comment, CrawlResult


def test_comment_to_dict():
    c = Comment(
        platform="京东",
        comment_id="123",
        content="外饰设计很漂亮",
        author="用户A",
        author_id="u001",
        publish_time="2024-01-01 10:00:00",
        likes=10,
        replies=2,
        source_url="https://item.jd.com/test.html",
        source_title="测试商品",
        keyword="汽车外饰",
    )
    d = c.to_dict()
    assert d["platform"] == "京东"
    assert d["comment_id"] == "123"
    assert d["content"] == "外饰设计很漂亮"
    assert d["likes"] == 10


def test_comment_to_json():
    c = Comment(
        platform="bilibili",
        comment_id="456",
        content="这个外饰改装真不错",
        author="用户B",
        author_id="u002",
        publish_time="2024-02-01",
    )
    j = c.to_json()
    parsed = json.loads(j)
    assert parsed["platform"] == "bilibili"
    assert parsed["content"] == "这个外饰改装真不错"


def test_comment_defaults():
    c = Comment(
        platform="知乎",
        comment_id="789",
        content="test",
        author="user",
        author_id="uid",
        publish_time="2024-03-01",
    )
    assert c.likes == 0
    assert c.replies == 0
    assert c.source_url == ""
    assert c.extra == {}
    assert c.crawled_at != ""


def test_crawl_result_to_dict():
    c = Comment(
        platform="小红书",
        comment_id="xhs1",
        content="外观好看",
        author="小红",
        author_id="xhsuid",
        publish_time="2024-04-01",
    )
    result = CrawlResult(
        platform="小红书",
        keyword="汽车外饰",
        total=1,
        comments=[c],
    )
    d = result.to_dict()
    assert d["platform"] == "小红书"
    assert d["total"] == 1
    assert len(d["comments"]) == 1
    assert d["success"] is True
    assert d["error"] is None


def test_crawl_result_failure():
    result = CrawlResult(
        platform="bilibili",
        keyword="改装",
        total=0,
        comments=[],
        success=False,
        error="Connection error",
    )
    d = result.to_dict()
    assert d["success"] is False
    assert d["error"] == "Connection error"
    assert d["total"] == 0
