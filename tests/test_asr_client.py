import numpy as np
import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from asr_client import ASRClient, load_hotwords


class TestLoadHotwords:
    def test_load_existing_file(self, tmp_path):
        f = tmp_path / "hotwords.txt"
        f.write_text("PyTorch\nFunASR\n", encoding="utf-8")
        result = load_hotwords(str(f))
        assert result == "PyTorch FunASR"

    def test_load_empty_file(self, tmp_path):
        f = tmp_path / "hotwords.txt"
        f.write_text("", encoding="utf-8")
        result = load_hotwords(str(f))
        assert result == ""

    def test_load_file_with_blank_lines(self, tmp_path):
        f = tmp_path / "hotwords.txt"
        f.write_text("PyTorch\n\n  FunASR  \n\n", encoding="utf-8")
        result = load_hotwords(str(f))
        assert result == "PyTorch FunASR"

    def test_load_missing_file(self):
        result = load_hotwords("/nonexistent/hotwords.txt")
        assert result == ""


class TestASRClient:
    @patch("asr_client.load_hotwords", return_value="")
    @patch("asr_client.AutoModel")
    def test_init_loads_model(self, mock_auto_model, mock_hw):
        client = ASRClient()
        mock_auto_model.assert_called_once_with(
            model="paraformer-zh",
            model_revision="v2.0.4",
            disable_update=True,
            trust_remote_code=True,
        )

    @patch("asr_client.load_hotwords", return_value="")
    @patch("asr_client.AutoModel")
    def test_transcribe_returns_text(self, mock_auto_model, mock_hw):
        mock_model = MagicMock()
        mock_model.generate.return_value = [{"text": "你好世界"}]
        mock_auto_model.return_value = mock_model

        client = ASRClient()
        audio = np.zeros(16000, dtype=np.float32)
        result = client.transcribe(audio)
        assert result == "你好世界"
        mock_model.generate.assert_called_once_with(input=audio, batch_size_s=300)

    @patch("asr_client.load_hotwords", return_value="PyTorch FunASR")
    @patch("asr_client.AutoModel")
    def test_transcribe_with_hotwords(self, mock_auto_model, mock_hw):
        mock_model = MagicMock()
        mock_model.generate.return_value = [{"text": "PyTorch框架"}]
        mock_auto_model.return_value = mock_model

        client = ASRClient()
        audio = np.zeros(16000, dtype=np.float32)
        result = client.transcribe(audio)
        assert result == "PyTorch框架"
        mock_model.generate.assert_called_once_with(
            input=audio, batch_size_s=300, hotword="PyTorch FunASR"
        )

    @patch("asr_client.load_hotwords", return_value="")
    @patch("asr_client.AutoModel")
    def test_transcribe_strips_whitespace(self, mock_auto_model, mock_hw):
        mock_model = MagicMock()
        mock_model.generate.return_value = [{"text": "  你好  "}]
        mock_auto_model.return_value = mock_model

        client = ASRClient()
        result = client.transcribe(np.zeros(16000, dtype=np.float32))
        assert result == "你好"

    @patch("asr_client.load_hotwords", return_value="")
    @patch("asr_client.AutoModel")
    def test_transcribe_empty_result(self, mock_auto_model, mock_hw):
        mock_model = MagicMock()
        mock_model.generate.return_value = []
        mock_auto_model.return_value = mock_model

        client = ASRClient()
        result = client.transcribe(np.zeros(16000, dtype=np.float32))
        assert result == ""

    @patch("asr_client.load_hotwords", return_value="")
    @patch("asr_client.AutoModel")
    def test_transcribe_none_text(self, mock_auto_model, mock_hw):
        mock_model = MagicMock()
        mock_model.generate.return_value = [{"text": None}]
        mock_auto_model.return_value = mock_model

        client = ASRClient()
        result = client.transcribe(np.zeros(16000, dtype=np.float32))
        assert result == ""

    @patch("asr_client.load_hotwords", return_value="")
    @patch("asr_client.AutoModel")
    def test_transcribe_empty_text(self, mock_auto_model, mock_hw):
        mock_model = MagicMock()
        mock_model.generate.return_value = [{"text": ""}]
        mock_auto_model.return_value = mock_model

        client = ASRClient()
        result = client.transcribe(np.zeros(16000, dtype=np.float32))
        assert result == ""
