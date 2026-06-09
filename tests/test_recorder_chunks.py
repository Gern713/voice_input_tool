"""Tests for recorder chunk callback mechanism."""
import numpy as np
import pytest
from unittest.mock import MagicMock
from recorder import AudioRecorder, CHUNK_SAMPLES


class TestChunkCallback:
    def test_callback_not_called_below_threshold(self):
        rec = AudioRecorder()
        cb = MagicMock()
        rec.set_chunk_callback(cb)

        # Simulate a chunk smaller than threshold
        small_chunk = np.zeros((1000, 1), dtype=np.int16)
        rec._chunk_buf = []
        rec._chunk_count = 0
        rec._callback(small_chunk, 1000, None, None)

        cb.assert_not_called()

    def test_callback_called_at_threshold(self):
        rec = AudioRecorder()
        cb = MagicMock()
        rec.set_chunk_callback(cb)

        # Simulate accumulating to threshold
        rec._chunk_buf = []
        rec._chunk_count = 0
        chunk_size = 1024
        num_chunks = (CHUNK_SAMPLES // chunk_size) + 1

        for _ in range(num_chunks):
            data = np.zeros((chunk_size, 1), dtype=np.int16)
            rec._callback(data, chunk_size, None, None)

        assert cb.call_count >= 1

    def test_callback_receives_float32(self):
        rec = AudioRecorder()
        received = []
        rec.set_chunk_callback(lambda a: received.append(a))

        rec._chunk_buf = []
        rec._chunk_count = 0
        big_chunk = np.ones((CHUNK_SAMPLES + 100, 1), dtype=np.int16)
        rec._callback(big_chunk, CHUNK_SAMPLES + 100, None, None)

        assert len(received) == 1
        assert received[0].dtype == np.float32

    def test_callback_exception_swallowed(self):
        rec = AudioRecorder()
        rec.set_chunk_callback(lambda a: 1 / 0)  # will raise

        rec._chunk_buf = []
        rec._chunk_count = 0
        big_chunk = np.ones((CHUNK_SAMPLES + 100, 1), dtype=np.int16)
        # Should not raise
        rec._callback(big_chunk, CHUNK_SAMPLES + 100, None, None)

    def test_no_callback_when_none(self):
        rec = AudioRecorder()
        rec.set_chunk_callback(None)

        rec._chunk_buf = []
        rec._chunk_count = 0
        big_chunk = np.ones((CHUNK_SAMPLES + 100, 1), dtype=np.int16)
        # Should not raise
        rec._callback(big_chunk, CHUNK_SAMPLES + 100, None, None)

    def test_buffer_resets_after_emit(self):
        rec = AudioRecorder()
        cb = MagicMock()
        rec.set_chunk_callback(cb)

        rec._chunk_buf = []
        rec._chunk_count = 0
        big_chunk = np.ones((CHUNK_SAMPLES + 100, 1), dtype=np.int16)
        rec._callback(big_chunk, CHUNK_SAMPLES + 100, None, None)

        assert cb.call_count == 1
        assert rec._chunk_count == 0
        assert rec._chunk_buf == []

    def test_frames_still_accumulated_with_callback(self):
        """chunk_callback should not interfere with normal frame accumulation."""
        rec = AudioRecorder()
        cb = MagicMock()
        rec.set_chunk_callback(cb)
        rec._frames = []

        data = np.ones((1024, 1), dtype=np.int16)
        rec._callback(data, 1024, None, None)

        assert len(rec._frames) == 1

    def test_set_callback_can_be_changed(self):
        rec = AudioRecorder()
        cb1 = MagicMock()
        cb2 = MagicMock()

        rec.set_chunk_callback(cb1)
        rec.set_chunk_callback(cb2)

        rec._chunk_buf = []
        rec._chunk_count = 0
        big_chunk = np.ones((CHUNK_SAMPLES + 100, 1), dtype=np.int16)
        rec._callback(big_chunk, CHUNK_SAMPLES + 100, None, None)

        cb1.assert_not_called()
        assert cb2.call_count == 1
