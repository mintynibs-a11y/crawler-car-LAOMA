"""
Tests for crawler modules using mocked HTTP responses.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.crawlers.bilibili import BilibiliCrawler
from src.crawlers.jd import JDCrawler
from src.crawlers.xiaohongshu import XiaohongshuCrawler
from src.crawlers.zhihu import ZhihuCrawler
from src.models import Comment, CrawlResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.text = json.dumps(json_data, ensure_ascii=False)
    mock.raise_for_status = MagicMock()
    return mock


# ---------------------------------------------------------------------------
# Bilibili
# ---------------------------------------------------------------------------

class TestBilibiliCrawler:
    def test_crawl_returns_crawl_result(self):
        crawler = BilibiliCrawler(max_pages=1)
        search_resp = _mock_response(
            {
                "data": {
                    "result": [
                        {"aid": "12345", "bvid": "BV1xx411c7mD", "title": "汽车外饰改装 视频"}
                    ]
                }
            }
        )
        comment_resp = _mock_response(
            {
                "data": {
                    "replies": [
                        {
                            "rpid": 1001,
                            "content": {"message": "外饰改装很好看"},
                            "member": {"uname": "用户甲", "mid": 9001},
                            "ctime": 1700000000,
                            "like": 5,
                            "rcount": 1,
                        }
                    ]
                }
            }
        )

        with patch.object(crawler.session, "get", side_effect=[search_resp, comment_resp, _mock_response({"data": {"replies": []}})]):
            result = crawler.crawl("汽车外饰")

        assert isinstance(result, CrawlResult)
        assert result.platform == "bilibili"
        assert result.success is True
        assert result.total >= 1
        assert result.comments[0].content == "外饰改装很好看"

    def test_crawl_handles_empty_search(self):
        crawler = BilibiliCrawler(max_pages=1)
        empty_resp = _mock_response({"data": {"result": []}})
        with patch.object(crawler.session, "get", return_value=empty_resp):
            result = crawler.crawl("汽车外饰")
        assert result.total == 0
        assert result.success is True

    def test_crawl_handles_network_error(self):
        # Network errors inside sub-methods are caught and logged; the crawl
        # completes gracefully with zero results rather than raising.
        crawler = BilibiliCrawler(max_pages=1)
        with patch.object(crawler.session, "get", side_effect=Exception("timeout")):
            result = crawler.crawl("汽车外饰")
        assert result.success is True
        assert result.total == 0


# ---------------------------------------------------------------------------
# 京东 (JD)
# ---------------------------------------------------------------------------

class TestJDCrawler:
    def test_crawl_uses_default_skus_when_search_fails(self):
        crawler = JDCrawler(max_pages=1)
        comment_resp = _mock_response(
            {
                "comments": [
                    {
                        "id": 2001,
                        "content": "贴膜质量不错，外饰效果好",
                        "nickname": "买家乙",
                        "guid": "g001",
                        "creationTime": "2024-01-15 10:00:00",
                        "usefulVoteCount": 3,
                        "replyCount": 0,
                        "score": 5,
                    }
                ]
            }
        )
        empty_resp = _mock_response({"comments": []})

        # search fails → uses default SKUs; then fetch comments
        with patch.object(crawler.session, "get", side_effect=Exception("search failed")):
            with patch.object(
                crawler, "_fetch_reviews", return_value=[
                    Comment(
                        platform="京东",
                        comment_id="2001",
                        content="贴膜质量不错，外饰效果好",
                        author="买家乙",
                        author_id="g001",
                        publish_time="2024-01-15 10:00:00",
                        keyword="汽车外饰",
                    )
                ]
            ):
                result = crawler.crawl("汽车外饰")

        assert isinstance(result, CrawlResult)

    def test_fetch_reviews_parses_comment_fields(self):
        crawler = JDCrawler(max_pages=1)
        data = {
            "comments": [
                {
                    "id": 3001,
                    "content": "外观设计时尚",
                    "nickname": "用户丙",
                    "guid": "g002",
                    "creationTime": "2024-02-01 09:00:00",
                    "usefulVoteCount": 7,
                    "replyCount": 2,
                    "score": 4,
                    "productColor": "黑色",
                }
            ]
        }
        empty = {"comments": []}
        with patch.object(crawler.session, "get", side_effect=[_mock_response(data), _mock_response(empty)]):
            comments = crawler._fetch_reviews("100047965793", "汽车外饰")
        assert len(comments) == 1
        assert comments[0].content == "外观设计时尚"
        assert comments[0].author == "用户丙"
        assert comments[0].likes == 7


# ---------------------------------------------------------------------------
# 小红书 (Xiaohongshu)
# ---------------------------------------------------------------------------

class TestXiaohongshuCrawler:
    def test_crawl_parses_notes_and_comments(self):
        crawler = XiaohongshuCrawler(max_pages=1)

        search_resp = _mock_response(
            {
                "data": {
                    "items": [
                        {
                            "note_card": {
                                "id": "note001",
                                "display_title": "汽车外饰改装分享",
                            }
                        }
                    ]
                }
            }
        )
        comment_resp = _mock_response(
            {
                "data": {
                    "comments": [
                        {
                            "id": "c001",
                            "content": "真的好看，想改装",
                            "user_info": {"nickname": "小红用户", "user_id": "xhs001"},
                            "create_time": 1700000000,
                            "like_count": 12,
                            "sub_comments": [],
                        }
                    ],
                    "cursor": "",
                    "has_more": False,
                }
            }
        )

        with patch.object(crawler.session, "post", return_value=search_resp):
            with patch.object(crawler.session, "get", return_value=comment_resp):
                result = crawler.crawl("汽车外饰")

        assert isinstance(result, CrawlResult)
        assert result.platform == "小红书"

    def test_crawl_handles_api_error(self):
        # API errors inside sub-methods are caught and logged; the crawl
        # completes gracefully with zero results rather than raising.
        crawler = XiaohongshuCrawler(max_pages=1)
        with patch.object(crawler.session, "post", side_effect=Exception("forbidden")):
            result = crawler.crawl("汽车外饰")
        assert result.success is True
        assert result.total == 0


# ---------------------------------------------------------------------------
# 知乎 (Zhihu)
# ---------------------------------------------------------------------------

class TestZhihuCrawler:
    def test_crawl_parses_questions_and_answers(self):
        crawler = ZhihuCrawler(max_pages=1)

        search_resp = _mock_response(
            {
                "data": [
                    {
                        "object": {
                            "type": "question",
                            "id": "q001",
                            "title": "汽车外饰设计有哪些值得关注的趋势？",
                            "url": "https://www.zhihu.com/question/q001",
                        }
                    }
                ]
            }
        )
        answer_resp = _mock_response(
            {
                "data": [
                    {
                        "id": "a001",
                        "content": "<p>外饰设计越来越注重空气动力学。</p>",
                        "author": {"name": "知乎用户甲", "id": "zh001"},
                        "updated_time": 1700000000,
                        "voteup_count": 100,
                        "comment_count": 5,
                    }
                ]
            }
        )

        with patch.object(crawler.session, "get", side_effect=[search_resp, answer_resp]):
            result = crawler.crawl("汽车外饰")

        assert isinstance(result, CrawlResult)
        assert result.platform == "知乎"
        assert result.total == 1
        assert "空气动力学" in result.comments[0].content

    def test_crawl_skips_non_question_results(self):
        crawler = ZhihuCrawler(max_pages=1)
        search_resp = _mock_response(
            {
                "data": [
                    {"object": {"type": "article", "id": "art001", "title": "文章"}},
                ]
            }
        )
        with patch.object(crawler.session, "get", return_value=search_resp):
            result = crawler.crawl("汽车外饰")
        assert result.total == 0
