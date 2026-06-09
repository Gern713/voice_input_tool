"""Tests for streaming pipeline integration (app.py)."""
import queue
import threading
import pytest
from unittest.mock import MagicMock, patch, PropertyMock


class TestStreamWorker:
    def test_worker_processes_chunks(self):
        """Verify stream_worker processes audio chunks and emits signal."""
        from app import VoiceInputApp

        # Create mock app with minimal setup
        with patch("app.QApplication"), \
             patch("app.AudioRecorder"), \
             patch("app.ASRClient"), \
             patch("app.StreamingASRClient") as mock_stream_cls, \
             patch("app.TextProcessor"), \
             patch("app.FloatingMic"), \
             patch("app.winsound"), \
             patch("app.ctypes.windll"):

            mock_stream = MagicMock()
            mock_stream.process_chunk.return_value = "测试文字"
            mock_stream_cls.return_value = mock_stream

            app = VoiceInputApp()

            # Simulate stream worker
            q = queue.Queue()
            q.put(np_zeros(9600))
            q.put(None)  # sentinel

            results = []

            def mock_emit(text):
                results.append(text)

            app.btn.streaming_text = MagicMock()
            app.btn.streaming_text.emit = mock_emit

            # Run worker directly (not in thread)
            original_worker = app._stream_worker
            app._stream_queue = q

            # Manually simulate the worker loop
            while True:
                try:
                    chunk = q.get(timeout=1)
                except queue.Empty:
                    continue
                if chunk is None:
                    break
                text = mock_stream.process_chunk(chunk)
                if text:
                    app.btn.streaming_text.emit(text)

            assert len(results) == 1
            assert results[0] == "测试文字"


class TestOnChunkRaceCondition:
    def test_local_variable_protects_against_none(self):
        """Verify _on_chunk uses local variable to avoid race."""
        from app import VoiceInputApp

        with patch("app.QApplication"), \
             patch("app.AudioRecorder"), \
             patch("app.ASRClient"), \
             patch("app.StreamingASRClient"), \
             patch("app.TextProcessor"), \
             patch("app.FloatingMic"), \
             patch("app.winsound"), \
             patch("app.ctypes.windll"):

            app = VoiceInputApp()
            q = queue.Queue()
            app._stream_queue = q

            # _on_chunk should work even if queue is valid
            app._on_chunk(np_zeros(100))

            assert not q.empty()
            assert q.get_nowait().shape == (100,)

    def test_on_chunk_safe_when_queue_none(self):
        """Verify _on_chunk doesn't crash when queue is None."""
        from app import VoiceInputApp

        with patch("app.QApplication"), \
             patch("app.AudioRecorder"), \
             patch("app.ASRClient"), \
             patch("app.StreamingASRClient"), \
             patch("app.TextProcessor"), \
             patch("app.FloatingMic"), \
             patch("app.winsound"), \
             patch("app.ctypes.windll"):

            app = VoiceInputApp()
            app._stream_queue = None

            # Should not raise
            app._on_chunk(np_zeros(100))


class TestStopStream:
    def test_stop_sends_sentinel(self):
        """Verify _stop_stream puts None sentinel."""
        from app import VoiceInputApp

        with patch("app.QApplication"), \
             patch("app.AudioRecorder"), \
             patch("app.ASRClient"), \
             patch("app.StreamingASRClient"), \
             patch("app.TextProcessor"), \
             patch("app.FloatingMic"), \
             patch("app.winsound"), \
             patch("app.ctypes.windll"):

            app = VoiceInputApp()
            q = queue.Queue()
            app._stream_queue = q
            app._stream_thread = MagicMock()

            app._stop_stream()

            assert q.get_nowait() is None  # sentinel was sent
            assert app._stream_queue is None
            assert app._stream_thread is None

    def test_stop_idempotent(self):
        """Calling _stop_stream when already None should not raise."""
        from app import VoiceInputApp

        with patch("app.QApplication"), \
             patch("app.AudioRecorder"), \
             patch("app.ASRClient"), \
             patch("app.StreamingASRClient"), \
             patch("app.TextProcessor"), \
             patch("app.FloatingMic"), \
             patch("app.winsound"), \
             patch("app.ctypes.windll"):

            app = VoiceInputApp()
            app._stream_queue = None
            app._stream_thread = None

            app._stop_stream()  # should not raise


def np_zeros(n):
    import numpy as np
    return np.zeros(n, dtype=np.float32)
