import pytest
from unittest.mock import patch, MagicMock, call

from ui import FloatingMic, HOTKEY_OPTIONS


class TestFloatingMicState:
    def _make_mic(self):
        mic = FloatingMic.__new__(FloatingMic)
        mic.state = FloatingMic.IDLE
        mic._pulse = 0
        mic._tick_count = 0
        mic._partial = ""
        mic._timer = MagicMock()
        mic._timeout_timer = MagicMock()
        mic._restore_timer = MagicMock()
        mic._pending_clip_restore = None
        mic.update = MagicMock()
        mic.setToolTip = MagicMock()
        mic.winId = MagicMock(return_value=12345)
        mic._settings = MagicMock()
        mic._hotkey_name = "F8"
        mic._hotkey_vk = HOTKEY_OPTIONS["F8"]
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
        assert mic._partial == ""
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
        assert mic._partial == ""

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


class TestSetHotkey:
    @patch("ui.ctypes")
    def test_set_hotkey_registers_new_key(self, mock_ctypes):
        mic = self._make_mic()
        mic.set_hotkey("F6")
        mock_ctypes.windll.user32.UnregisterHotKey.assert_called_once_with(12345, 1)
        mock_ctypes.windll.user32.RegisterHotKey.assert_called_once_with(12345, 1, 0, HOTKEY_OPTIONS["F6"])
        assert mic._hotkey_name == "F6"
        assert mic._hotkey_vk == HOTKEY_OPTIONS["F6"]
        mic._settings.setValue.assert_called_with("hotkey", "F6")

    @patch("ui.ctypes")
    def test_set_hotkey_updates_tooltip(self, mock_ctypes):
        mic = self._make_mic()
        mic.set_hotkey("F10")
        mic.setToolTip.assert_called_once()
        assert "F10" in mic.setToolTip.call_args[0][0]

    def test_set_hotkey_same_key_noop(self):
        mic = self._make_mic()
        mic._hotkey_vk = HOTKEY_OPTIONS["F8"]
        mic.set_hotkey("F8")
        mic._settings.setValue.assert_not_called()

    def test_set_hotkey_invalid_name_noop(self):
        mic = self._make_mic()
        mic.set_hotkey("F1")
        mic._settings.setValue.assert_not_called()

    def _make_mic(self):
        mic = FloatingMic.__new__(FloatingMic)
        mic.state = FloatingMic.IDLE
        mic._pulse = 0
        mic._tick_count = 0
        mic._partial = ""
        mic._timer = MagicMock()
        mic._timeout_timer = MagicMock()
        mic.update = MagicMock()
        mic.setToolTip = MagicMock()
        mic.winId = MagicMock(return_value=12345)
        mic._settings = MagicMock()
        mic._hotkey_name = "F8"
        mic._hotkey_vk = HOTKEY_OPTIONS["F8"]
        return mic


class TestPartialText:
    def _make_mic(self):
        mic = FloatingMic.__new__(FloatingMic)
        mic.state = FloatingMic.IDLE
        mic._pulse = 0
        mic._tick_count = 0
        mic._partial = ""
        mic._timer = MagicMock()
        mic._timeout_timer = MagicMock()
        mic.update = MagicMock()
        return mic

    def test_on_partial_text_updates_display(self):
        mic = self._make_mic()
        mic._on_partial_text("你好世界")
        assert mic._partial == "你好世界"
        mic.update.assert_called_once()

    def test_partial_cleared_on_idle(self):
        mic = self._make_mic()
        mic._partial = "测试"
        mic.set_state(FloatingMic.IDLE)
        assert mic._partial == ""

    def test_partial_cleared_on_new_recording(self):
        mic = self._make_mic()
        mic._partial = "旧的文字"
        mic.set_state(FloatingMic.RECORDING)
        assert mic._partial == ""
