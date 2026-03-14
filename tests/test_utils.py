"""
Tests for utility functions.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from src.utils import save_csv, save_json, build_session, rate_limit


def test_build_session_returns_session():
    import requests
    session = build_session()
    assert isinstance(session, requests.Session)
    assert "User-Agent" in session.headers


def test_build_session_applies_extra_headers():
    session = build_session(extra_headers={"X-Custom": "test"})
    assert session.headers["X-Custom"] == "test"


def test_save_json_creates_file():
    data = [{"platform": "bilibili", "content": "测试评论"}]
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.json"
        save_json(data, path)
        assert path.exists()
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert len(loaded) == 1
        assert loaded[0]["platform"] == "bilibili"


def test_save_json_creates_parent_dirs():
    data = [{"a": 1}]
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "nested" / "deep" / "out.json"
        save_json(data, path)
        assert path.exists()


def test_save_csv_creates_file():
    data = [{"platform": "京东", "content": "不错", "likes": 5}]
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.csv"
        save_csv(data, path)
        assert path.exists()
        text = path.read_text(encoding="utf-8-sig")
        assert "platform" in text
        assert "京东" in text


def test_save_csv_empty_data_does_not_create_file(caplog):
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "empty.csv"
        save_csv([], path)
        assert not path.exists()


def test_rate_limit_sleeps(monkeypatch):
    calls = []
    monkeypatch.setattr("src.utils.time.sleep", lambda s: calls.append(s))
    rate_limit(0.5, 1.5)
    assert len(calls) == 1
    assert 0.5 <= calls[0] <= 1.5
