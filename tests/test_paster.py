import pytest
from unittest.mock import patch, MagicMock, call
import paster


class TestPaster:
    @patch.object(paster, "pyperclip")
    @patch.object(paster, "time")
    def test_paste_copies_text(self, mock_time, mock_clip):
        paster.paste_text("new text")
        mock_clip.copy.assert_called_with("new text")

    @patch.object(paster, "pyperclip")
    @patch.object(paster, "time")
    def test_paste_no_restore_old_clipboard(self, mock_time, mock_clip):
        paster.paste_text("test")
        mock_clip.copy.assert_called_once_with("test")

    @patch.object(paster, "pyperclip")
    @patch.object(paster, "time")
    def test_paste_calls_sleep(self, mock_time, mock_clip):
        paster.paste_text("test")
        assert mock_time.sleep.call_count >= 2

    @patch.object(paster, "pyperclip")
    @patch.object(paster, "time")
    def test_paste_empty_text_still_works(self, mock_time, mock_clip):
        paster.paste_text("")
        mock_clip.copy.assert_called_with("")

    @patch.object(paster, "pyperclip")
    @patch.object(paster, "time")
    def test_paste_with_target_hwnd(self, mock_time, mock_clip):
        mock_user32 = MagicMock()
        with patch("ctypes.windll", create=True) as mock_windll:
            mock_windll.user32 = mock_user32
            paster.paste_text("hello", target_hwnd=12345)
            mock_user32.SetForegroundWindow.assert_called_with(12345)

    @patch.object(paster, "pyperclip")
    @patch.object(paster, "time")
    def test_paste_without_hwnd_skips_setforeground(self, mock_time, mock_clip):
        paster.paste_text("hello", target_hwnd=None)
        mock_clip.copy.assert_called_once_with("hello")
