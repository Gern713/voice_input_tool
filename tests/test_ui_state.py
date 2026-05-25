import pytest
from unittest.mock import MagicMock

from ui import FloatingMic


class TestFloatingMicState:
    def _make_mic(self):
        mic = FloatingMic.__new__(FloatingMic)
        mic.state = FloatingMic.IDLE
        mic._pulse = 0
        mic._tick_count = 0
        mic._timer = MagicMock()
        mic._timeout_timer = MagicMock()
        mic._restore_timer = MagicMock()
        mic._pending_clip_restore = None
        mic.update = MagicMock()
        return mic

    def test_initial_state_is_idle(self):
        mic = self._make_mic()
        assert mic.state == "idle"

    def test_idle_to_recording(self):
        mic = self._make_mic()
        mic.set_state(FloatingMic.RECORDING)
        assert mic.state == "recording"
        assert mic._pulse == 0
        assert mic._tick_count == 0
        mic._timer.start.assert_called_once()

    def test_recording_to_processing(self):
        mic = self._make_mic()
        mic.set_state(FloatingMic.RECORDING)
        mic.set_state(FloatingMic.PROCESSING)
        assert mic.state == "processing"
        mic._timer.stop.assert_called()

    def test_processing_to_idle(self):
        mic = self._make_mic()
        mic.set_state(FloatingMic.RECORDING)
        mic.set_state(FloatingMic.PROCESSING)
        mic.set_state(FloatingMic.IDLE)
        assert mic.state == "idle"
        mic._timer.stop.assert_called()
        mic._timeout_timer.stop.assert_called()

    def test_full_cycle(self):
        mic = self._make_mic()
        assert mic.state == FloatingMic.IDLE
        mic.set_state(FloatingMic.RECORDING)
        assert mic.state == FloatingMic.RECORDING
        mic.set_state(FloatingMic.PROCESSING)
        assert mic.state == FloatingMic.PROCESSING
        mic.set_state(FloatingMic.IDLE)
        assert mic.state == FloatingMic.IDLE

    def test_do_reset_returns_to_idle(self):
        mic = self._make_mic()
        mic.set_state(FloatingMic.RECORDING)
        mic._do_reset()
        assert mic.state == FloatingMic.IDLE
