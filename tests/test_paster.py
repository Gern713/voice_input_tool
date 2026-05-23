import pytest
from unittest.mock import patch, MagicMock, call
import paster


class TestPaster:
    @patch.object(paster, "pyperclip")
    @patch.object(paster, "time")
    @patch.object(paster, "_simulate_paste")
    def test_paste_copies_text(self, mock_sim, mock_time, mock_clip):
        mock_clip.paste.return_value = "old"
        paster.paste_text("new text")
        mock_clip.copy.assert_any_call("new text")
        mock_sim.assert_called_once()

    @patch.object(paster, "pyperclip")
    @patch.object(paster, "time")
    @patch.object(paster, "_simulate_paste")
    def test_paste_restores_clipboard(self, mock_sim, mock_time, mock_clip):
        mock_clip.paste.return_value = "old content"
        paster.paste_text("test")
        calls = mock_clip.copy.call_args_list
        assert calls[0] == call("test")
        assert calls[-1] == call("old content")

    @patch.object(paster, "pyperclip")
    @patch.object(paster, "time")
    @patch.object(paster, "_simulate_paste")
    def test_paste_calls_sleep(self, mock_sim, mock_time, mock_clip):
        mock_clip.paste.return_value = ""
        paster.paste_text("test")
        assert mock_time.sleep.call_count >= 2

    @patch.object(paster, "pyperclip")
    @patch.object(paster, "time")
    @patch.object(paster, "_simulate_paste")
    def test_paste_handles_clipboard_read_error(self, mock_sim, mock_time, mock_clip):
        mock_clip.paste.side_effect = Exception("clipboard error")
        paster.paste_text("test")
        mock_clip.copy.assert_any_call("test")

    @patch.object(paster, "pyperclip")
    @patch.object(paster, "time")
    @patch.object(paster, "_simulate_paste")
    def test_paste_empty_text_still_works(self, mock_sim, mock_time, mock_clip):
        mock_clip.paste.return_value = ""
        paster.paste_text("")
        mock_clip.copy.assert_called_with("")

    @patch.object(paster, "pyperclip")
    @patch.object(paster, "time")
    @patch.object(paster, "_simulate_paste")
    def test_paste_handles_restore_error(self, mock_sim, mock_time, mock_clip):
        mock_clip.paste.return_value = "old"
        mock_clip.copy.side_effect = [None, Exception("restore fail")]
        paster.paste_text("test")
        mock_sim.assert_called_once()
