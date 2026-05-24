import pytest
from unittest.mock import patch, MagicMock, call

from ui import FloatingMic


class TestPasteFlow:
    def _make_mic(self):
        mic = FloatingMic.__new__(FloatingMic)
        mic.state = FloatingMic.IDLE
        mic._pulse = 0
        mic._tick_count = 0
        mic._timer = MagicMock()
        mic._timeout_timer = MagicMock()
        mic._target_hwnd = 12345
        mic._tray_ref = MagicMock()
        return mic

    @patch("ui.pyperclip")
    @patch("ui.time")
    @patch("ui.ctypes")
    def test_paste_copies_text(self, mock_ctypes, mock_time, mock_clip):
        mic = self._make_mic()
        mic.hide = MagicMock()
        mic.show = MagicMock()
        mic._do_paste_and_notify("hello world")
        mock_clip.copy.assert_any_call("hello world")

    @patch("ui.pyperclip")
    @patch("ui.time")
    @patch("ui.ctypes")
    def test_paste_saves_old_clipboard(self, mock_ctypes, mock_time, mock_clip):
        mock_clip.paste.return_value = "old text"
        mic = self._make_mic()
        mic.hide = MagicMock()
        mic.show = MagicMock()
        mic._do_paste_and_notify("new text")
        calls = mock_clip.copy.call_args_list
        assert calls[0] == call("new text")
        assert calls[-1] == call("old text")

    @patch("ui.pyperclip")
    @patch("ui.time")
    @patch("ui.ctypes")
    def test_paste_no_restore_when_old_is_none(self, mock_ctypes, mock_time, mock_clip):
        mock_clip.paste.side_effect = Exception("no clipboard")
        mic = self._make_mic()
        mic.hide = MagicMock()
        mic.show = MagicMock()
        mic._do_paste_and_notify("text")
        mock_clip.copy.assert_called_once_with("text")

    @patch("ui.pyperclip")
    @patch("ui.time")
    @patch("ui.ctypes")
    def test_paste_sets_foreground(self, mock_ctypes, mock_time, mock_clip):
        mic = self._make_mic()
        mic.hide = MagicMock()
        mic.show = MagicMock()
        mic._do_paste_and_notify("text")
        mock_ctypes.windll.user32.SetForegroundWindow.assert_called_with(12345)

    @patch("ui.pyperclip")
    @patch("ui.time")
    @patch("ui.ctypes")
    def test_paste_simulates_ctrl_v(self, mock_ctypes, mock_time, mock_clip):
        mic = self._make_mic()
        mic.hide = MagicMock()
        mic.show = MagicMock()
        mic._do_paste_and_notify("text")
        user32 = mock_ctypes.windll.user32
        key_calls = user32.keybd_event.call_args_list
        assert len(key_calls) == 4
        assert key_calls[0] == call(0x11, 0, 0, 0)
        assert key_calls[1] == call(0x56, 0, 0, 0)
        assert key_calls[2] == call(0x56, 0, 2, 0)
        assert key_calls[3] == call(0x11, 0, 2, 0)

    @patch("ui.pyperclip")
    @patch("ui.time")
    @patch("ui.ctypes")
    def test_paste_shows_tray_notification(self, mock_ctypes, mock_time, mock_clip):
        mic = self._make_mic()
        mic.hide = MagicMock()
        mic.show = MagicMock()
        mic._do_paste_and_notify("test msg")
        mic._tray_ref.showMessage.assert_called_once()

    @patch("ui.pyperclip")
    @patch("ui.time")
    @patch("ui.ctypes")
    def test_paste_without_target_hwnd(self, mock_ctypes, mock_time, mock_clip):
        mic = self._make_mic()
        mic._target_hwnd = None
        mic.hide = MagicMock()
        mic.show = MagicMock()
        mic._do_paste_and_notify("text")
        mock_ctypes.windll.user32.SetForegroundWindow.assert_not_called()
