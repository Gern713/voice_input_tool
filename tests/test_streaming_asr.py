"""Tests for StreamingASRClient."""
import numpy as np
import pytest
from unittest.mock import patch, MagicMock


class TestStreamingASRClientInit:
    @patch("asr_client.AutoModel")
    def test_model_loaded_with_correct_name(self, mock_auto):
        from asr_client import StreamingASRClient
        client = StreamingASRClient()
        call_kwargs = mock_auto.call_args[1]
        assert call_kwargs["model"] == "paraformer-zh-streaming"
        assert call_kwargs["model_revision"] == "v2.0.4"

    @patch("asr_client.AutoModel")
    def test_cache_initially_empty(self, mock_auto):
        from asr_client import StreamingASRClient
        client = StreamingASRClient()
        assert client._cache == {}


class TestStreamingASRClientProcess:
    @patch("asr_client.AutoModel")
    def test_process_chunk_returns_text(self, mock_auto):
        mock_model = MagicMock()
        mock_auto.return_value = mock_model
        mock_model.generate.return_value = [{"text": "你好世界"}]

        from asr_client import StreamingASRClient
        client = StreamingASRClient()
        audio = np.zeros(9600, dtype=np.float32)
        result = client.process_chunk(audio)
        assert result == "你好世界"

    @patch("asr_client.AutoModel")
    def test_process_chunk_empty_result(self, mock_auto):
        mock_model = MagicMock()
        mock_auto.return_value = mock_model
        mock_model.generate.return_value = [{}]

        from asr_client import StreamingASRClient
        client = StreamingASRClient()
        audio = np.zeros(9600, dtype=np.float32)
        result = client.process_chunk(audio)
        assert result == ""

    @patch("asr_client.AutoModel")
    def test_process_chunk_passes_cache(self, mock_auto):
        mock_model = MagicMock()
        mock_auto.return_value = mock_model
        mock_model.generate.return_value = [{"text": "test"}]

        from asr_client import StreamingASRClient
        client = StreamingASRClient()
        audio = np.zeros(9600, dtype=np.float32)
        client.process_chunk(audio)

        call_kwargs = mock_model.generate.call_args[1]
        assert "cache" in call_kwargs
        assert "chunk_size" in call_kwargs
        assert call_kwargs["chunk_size"] == [0, 10, 5]

    @patch("asr_client.AutoModel")
    def test_reset_clears_cache(self, mock_auto):
        from asr_client import StreamingASRClient
        client = StreamingASRClient()
        client._cache = {"some": "data"}
        client.reset()
        assert client._cache == {}


class TestStreamingASRClientChunkParams:
    @patch("asr_client.AutoModel")
    def test_encoder_decoder_lookback(self, mock_auto):
        mock_model = MagicMock()
        mock_auto.return_value = mock_model
        mock_model.generate.return_value = [{"text": "x"}]

        from asr_client import StreamingASRClient
        client = StreamingASRClient()
        client.process_chunk(np.zeros(100, dtype=np.float32))

        kwargs = mock_model.generate.call_args[1]
        assert kwargs["encoder_chunk_look_back"] == 4
        assert kwargs["decoder_chunk_look_back"] == 1

    @patch("asr_client.AutoModel")
    def test_is_final_passed_through(self, mock_auto):
        mock_model = MagicMock()
        mock_auto.return_value = mock_model
        mock_model.generate.return_value = [{"text": "x"}]

        from asr_client import StreamingASRClient
        client = StreamingASRClient()
        client.process_chunk(np.zeros(100, dtype=np.float32), is_final=True)

        kwargs = mock_model.generate.call_args[1]
        assert kwargs["is_final"] is True
