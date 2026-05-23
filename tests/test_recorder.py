import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from recorder import AudioRecorder


class TestAudioRecorder:
    def test_init(self):
        rec = AudioRecorder()
        assert rec.sr == 16000
        assert rec._frames == []
        assert rec._thread is None

    def test_start_resets_state(self):
        rec = AudioRecorder()
        rec._frames = [np.zeros((100, 1))]
        rec._stop_event.set()
        rec.start()
        assert rec._frames == []
        assert not rec._stop_event.is_set()
        assert rec._thread is not None
        rec._stop_event.set()
        rec._thread.join(timeout=2)

    def test_stop_returns_none_when_no_frames(self):
        rec = AudioRecorder()
        result = rec.stop()
        assert result is None

    def test_stop_returns_none_when_too_short(self):
        rec = AudioRecorder()
        rec._frames = [np.zeros((100, 1))]
        rec._stop_event.set()
        result = rec.stop()
        assert result is None

    def test_stop_returns_audio_when_long_enough(self):
        rec = AudioRecorder()
        rec._frames = [np.ones((8000, 1)) for _ in range(3)]
        rec._stop_event.set()
        result = rec.stop()
        assert result is not None
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32
        assert len(result) == 24000

    def test_callback_appends_frames(self):
        rec = AudioRecorder()
        mock_data = np.ones((1024, 1), dtype=np.int16)
        rec._callback(mock_data, 1024, None, None)
        assert len(rec._frames) == 1
        np.testing.assert_array_equal(rec._frames[0], mock_data)

    def test_callback_appends_copies(self):
        rec = AudioRecorder()
        mock_data = np.ones((1024, 1), dtype=np.int16)
        rec._callback(mock_data, 1024, None, None)
        mock_data[:] = 0
        assert not np.array_equal(rec._frames[0], mock_data)

    def test_stop_joins_thread(self):
        rec = AudioRecorder()
        rec.start()
        assert rec._thread is not None
        rec.stop()
        assert rec._thread is None

    def test_minimum_duration_threshold(self):
        rec = AudioRecorder()
        sr = rec.sr
        min_samples = int(sr * 0.3)
        rec._frames = [np.zeros((min_samples - 1, 1))]
        rec._stop_event.set()
        result = rec.stop()
        assert result is None

        rec._frames = [np.zeros((min_samples + 1, 1))]
        rec._stop_event.set()
        result = rec.stop()
        assert result is not None

    @patch("recorder.sd.InputStream")
    def test_run_opens_stream(self, mock_stream_cls):
        mock_stream = MagicMock()
        mock_stream_cls.return_value.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream_cls.return_value.__exit__ = MagicMock(return_value=False)
        rec = AudioRecorder()
        rec._stop_event.set()
        rec._run()
        mock_stream_cls.assert_called_once_with(
            samplerate=16000, channels=1, dtype="int16",
            blocksize=1024, callback=rec._callback,
        )
