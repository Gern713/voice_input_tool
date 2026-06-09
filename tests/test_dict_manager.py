"""Tests for dict_manager module."""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Avoid QSettings at import time — patch before importing dict_manager
import sys
sys.modules.setdefault("PySide6.QtCore", MagicMock())


class TestLoadDictFile:
    def test_load_existing_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("word1\nword2\nword3\n", encoding="utf-8")
        import dict_manager
        words = dict_manager._load_dict_file(str(f))
        assert words == ["word1", "word2", "word3"]

    def test_load_skips_empty_lines(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("word1\n\n\nword2\n  \n", encoding="utf-8")
        import dict_manager
        words = dict_manager._load_dict_file(str(f))
        assert words == ["word1", "word2"]

    def test_load_nonexistent_file(self):
        import dict_manager
        words = dict_manager._load_dict_file("/nonexistent/path.txt")
        assert words == []


class TestDictRegistry:
    def test_all_dicts_have_entries(self):
        import dict_manager
        assert len(dict_manager._DICT_REGISTRY) == 5
        for key in ["medical", "legal", "tech", "finance", "gaming"]:
            assert key in dict_manager._DICT_REGISTRY

    def test_base_url_is_github_raw(self):
        import dict_manager
        assert "raw.githubusercontent.com" in dict_manager._BASE_URL
        assert "Gern713/voice_input_tool" in dict_manager._BASE_URL


class TestDownloadDict:
    def test_skip_if_already_cached(self, tmp_path):
        import dict_manager
        dest = tmp_path / "test.txt"
        dest.write_text("cached", encoding="utf-8")
        with patch.object(dict_manager, "DICTS_DIR", tmp_path):
            # Should not attempt download
            dict_manager._download_dict("test")  # file exists, skips
            assert dest.read_text() == "cached"

    def test_download_failure_handled(self, tmp_path):
        import dict_manager
        with patch.object(dict_manager, "DICTS_DIR", tmp_path):
            with patch("urllib.request.urlretrieve", side_effect=Exception("network error")):
                dict_manager._download_dict("nonexistent")  # should not raise


class TestToggleDict:
    @patch("dict_manager._download_dict")
    @patch("dict_manager._settings")
    def test_enable_adds_key(self, mock_settings_fn, mock_download):
        mock_settings = MagicMock()
        mock_settings.value.return_value = []
        mock_settings_fn.return_value = mock_settings

        import dict_manager
        dict_manager.toggle_dict("tech", True)

        saved = mock_settings.setValue.call_args[0][1]
        assert "tech" in saved
        mock_download.assert_called_once_with("tech")

    @patch("dict_manager._download_dict")
    @patch("dict_manager._settings")
    def test_disable_removes_key(self, mock_settings_fn, mock_download):
        mock_settings = MagicMock()
        mock_settings.value.return_value = ["medical", "tech"]
        mock_settings_fn.return_value = mock_settings

        import dict_manager
        dict_manager.toggle_dict("tech", False)

        saved = mock_settings.setValue.call_args[0][1]
        assert "tech" not in saved
        assert "medical" in saved

    @patch("dict_manager._download_dict")
    @patch("dict_manager._settings")
    def test_handles_string_return(self, mock_settings_fn, mock_download):
        """QSettings sometimes returns a single string instead of list."""
        mock_settings = MagicMock()
        mock_settings.value.return_value = "medical"  # string, not list
        mock_settings_fn.return_value = mock_settings

        import dict_manager
        dict_manager.toggle_dict("tech", True)

        saved = mock_settings.setValue.call_args[0][1]
        assert "medical" in saved
        assert "tech" in saved


class TestLoadAllHotwords:
    @patch("dict_manager._settings")
    def test_merges_hotwords_and_dicts(self, mock_settings_fn, tmp_path):
        hotwords_file = tmp_path / "hotwords.txt"
        hotwords_file.write_text("PyTorch\nFunASR\n", encoding="utf-8")

        dict_file = tmp_path / "tech.txt"
        dict_file.write_text("Kubernetes\nDocker\n", encoding="utf-8")

        mock_settings = MagicMock()
        mock_settings.value.return_value = ["tech"]
        mock_settings_fn.return_value = mock_settings

        import dict_manager
        with patch.object(dict_manager, "DICTS_DIR", tmp_path):
            result = dict_manager.load_all_hotwords(str(hotwords_file))

        assert "PyTorch" in result
        assert "FunASR" in result
        assert "Kubernetes" in result
        assert "Docker" in result

    @patch("dict_manager._settings")
    def test_no_dicts_enabled(self, mock_settings_fn, tmp_path):
        hotwords_file = tmp_path / "hotwords.txt"
        hotwords_file.write_text("word1\n", encoding="utf-8")

        mock_settings = MagicMock()
        mock_settings.value.return_value = []
        mock_settings_fn.return_value = mock_settings

        import dict_manager
        result = dict_manager.load_all_hotwords(str(hotwords_file))
        assert result == "word1"

    @patch("dict_manager._settings")
    def test_no_hotwords_file(self, mock_settings_fn):
        mock_settings = MagicMock()
        mock_settings.value.return_value = []
        mock_settings_fn.return_value = mock_settings

        import dict_manager
        result = dict_manager.load_all_hotwords(None)
        assert result == ""

    @patch("dict_manager._settings")
    def test_missing_cached_dict_skipped(self, mock_settings_fn, tmp_path):
        hotwords_file = tmp_path / "hotwords.txt"
        hotwords_file.write_text("word1\n", encoding="utf-8")

        mock_settings = MagicMock()
        mock_settings.value.return_value = ["nonexistent_dict"]
        mock_settings_fn.return_value = mock_settings

        import dict_manager
        with patch.object(dict_manager, "DICTS_DIR", tmp_path):
            result = dict_manager.load_all_hotwords(str(hotwords_file))
        # nonexistent dict file is skipped, only hotwords returned
        assert result == "word1"
