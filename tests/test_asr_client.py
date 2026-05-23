import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from asr_client import ASRClient


class TestASRClient:
    @patch("asr_client.AutoModel")
    def test_init_loads_model(self, mock_auto_model):
        client = ASRClient()
        mock_auto_model.assert_called_once_with(
            model="paraformer-zh",
            model_revision="v2.0.4",
            disable_update=True,
            trust_remote_code=True,
        )

    @patch("asr_client.AutoModel")
    def test_transcribe_returns_text(self, mock_auto_model):
        mock_model = MagicMock()
        mock_model.generate.return_value = [{"text": "你好世界"}]
        mock_auto_model.return_value = mock_model

        client = ASRClient()
        audio = np.zeros(16000, dtype=np.float32)
        result = client.transcribe(audio)
        assert result == "你好世界"
        mock_model.generate.assert_called_once_with(input=audio, batch_size_s=300)

    @patch("asr_client.AutoModel")
    def test_transcribe_strips_whitespace(self, mock_auto_model):
        mock_model = MagicMock()
        mock_model.generate.return_value = [{"text": "  你好  "}]
        mock_auto_model.return_value = mock_model

        client = ASRClient()
        result = client.transcribe(np.zeros(16000, dtype=np.float32))
        assert result == "你好"

    @patch("asr_client.AutoModel")
    def test_transcribe_empty_result(self, mock_auto_model):
        mock_model = MagicMock()
        mock_model.generate.return_value = []
        mock_auto_model.return_value = mock_model

        client = ASRClient()
        result = client.transcribe(np.zeros(16000, dtype=np.float32))
        assert result == ""

    @patch("asr_client.AutoModel")
    def test_transcribe_none_text(self, mock_auto_model):
        mock_model = MagicMock()
        mock_model.generate.return_value = [{"text": None}]
        mock_auto_model.return_value = mock_model

        client = ASRClient()
        result = client.transcribe(np.zeros(16000, dtype=np.float32))
        assert result == ""

    @patch("asr_client.AutoModel")
    def test_transcribe_empty_text(self, mock_auto_model):
        mock_model = MagicMock()
        mock_model.generate.return_value = [{"text": ""}]
        mock_auto_model.return_value = mock_model

        client = ASRClient()
        result = client.transcribe(np.zeros(16000, dtype=np.float32))
        assert result == ""
