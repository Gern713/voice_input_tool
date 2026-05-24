import json
import pytest
from unittest.mock import patch
from pathlib import Path

import history


class TestHistoryLoad:
    def test_load_returns_empty_when_file_missing(self, tmp_path):
        with patch.object(history, "HISTORY_FILE", tmp_path / "nope.json"):
            assert history.load() == []

    def test_load_returns_empty_when_invalid_json(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("not json", encoding="utf-8")
        with patch.object(history, "HISTORY_FILE", f):
            assert history.load() == []

    def test_load_returns_list(self, tmp_path):
        f = tmp_path / "hist.json"
        f.write_text('[{"text":"hello"}]', encoding="utf-8")
        with patch.object(history, "HISTORY_FILE", f):
            assert history.load() == [{"text": "hello"}]


class TestHistorySave:
    def test_save_writes_json(self, tmp_path):
        f = tmp_path / "hist.json"
        with patch.object(history, "HISTORY_FILE", f):
            history.save([{"text": "abc"}])
        data = json.loads(f.read_text(encoding="utf-8"))
        assert data == [{"text": "abc"}]

    def test_save_truncates_to_max(self, tmp_path):
        f = tmp_path / "hist.json"
        items = [{"text": f"item{i}"} for i in range(15)]
        with patch.object(history, "HISTORY_FILE", f):
            history.save(items)
        data = json.loads(f.read_text(encoding="utf-8"))
        assert len(data) == 10
        assert data[0]["text"] == "item5"


class TestHistoryAdd:
    def test_add_appends_to_existing(self, tmp_path):
        f = tmp_path / "hist.json"
        f.write_text('[{"text":"old"}]', encoding="utf-8")
        with patch.object(history, "HISTORY_FILE", f):
            history.add("new")
        data = json.loads(f.read_text(encoding="utf-8"))
        assert len(data) == 2
        assert data[1]["text"] == "new"

    def test_add_creates_file_if_missing(self, tmp_path):
        f = tmp_path / "hist.json"
        with patch.object(history, "HISTORY_FILE", f):
            history.add("first")
        data = json.loads(f.read_text(encoding="utf-8"))
        assert data == [{"text": "first"}]
