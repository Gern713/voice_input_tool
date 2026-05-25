import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from asr_client import StreamingASRClient


class TestStreamingASRClient:
    @patch("asr_client.AutoModel")
    def test_init_loads_streaming_model(self, mock_auto_model):
        client = StreamingASRClient()
        mock_auto_model.assert_called_once_with(
            model="paraformer-zh-streaming",
            disable_update=True,
            trust_remote_code=True,
        )
        assert client._cache == {}

    @patch("asr_client.AutoModel")
    def test_process_chunk_returns_text(self, mock_auto_model):
        mock_model = MagicMock()
        mock_model.generate.return_value = [{"text": "你好"}]
        mock_auto_model.return_value = mock_model

        client = StreamingASRClient()
        audio = np.zeros(9600, dtype=np.float32)
        result = client.process_chunk(audio)
        assert result == "你好"
        mock_model.generate.assert_called_once_with(
            input=audio, cache=client._cache, is_final=False, chunk_size=[0, 10, 5]
        )

    @patch("asr_client.AutoModel")
    def test_process_chunk_empty_result(self, mock_auto_model):
        mock_model = MagicMock()
        mock_model.generate.return_value = []
        mock_auto_model.return_value = mock_model

        client = StreamingASRClient()
        result = client.process_chunk(np.zeros(9600, dtype=np.float32))
        assert result == ""

    @patch("asr_client.AutoModel")
    def test_end_session_returns_text(self, mock_auto_model):
        mock_model = MagicMock()
        mock_model.generate.return_value = [{"text": "你好世界"}]
        mock_auto_model.return_value = mock_model

        client = StreamingASRClient()
        audio = np.zeros(9600, dtype=np.float32)
        result = client.end_session(audio)
        assert result == "你好世界"
        mock_model.generate.assert_called_once_with(
            input=audio, cache=client._cache, is_final=True, chunk_size=[0, 10, 5]
        )

    @patch("asr_client.AutoModel")
    def test_end_session_resets_cache(self, mock_auto_model):
        mock_model = MagicMock()
        mock_model.generate.return_value = [{"text": "世界"}]
        mock_auto_model.return_value = mock_model

        client = StreamingASRClient()
        client._cache = {"some": "data"}
        client.end_session(np.zeros(100, dtype=np.float32))
        assert client._cache == {}
