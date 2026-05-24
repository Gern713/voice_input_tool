import sys
import winreg
import pytest
from unittest.mock import patch, MagicMock
import numpy as np

sys.modules["sounddevice"] = MagicMock()

import app as app_module


class TestFullPipeline:
    def _make_app(self):
        app_module.VoiceInputApp.__init__ = lambda self: None
        app = app_module.VoiceInputApp.__new__(app_module.VoiceInputApp)
        app.recorder = MagicMock()
        app.asr = MagicMock()
        app.processor = MagicMock()
        app.btn = MagicMock()
        app.btn.state = "idle"
        app._correction_enabled = True
        app.tray = MagicMock()
        app._refresh_tray_menu = MagicMock()
        return app

    def test_process_happy_path(self):
        app = self._make_app()
        app.asr.transcribe.return_value = "你好世界"
        app.processor.improve.return_value = "你好，世界！"

        app._process(np.zeros(16000, dtype=np.float32))

        app.asr.transcribe.assert_called_once()
        app.processor.improve.assert_called_once_with("你好世界")
        app.btn.paste_and_notify.emit.assert_called_once_with("你好，世界！")
        app.btn.reset_requested.emit.assert_called_once()

    def test_process_empty_asr(self):
        app = self._make_app()
        app.asr.transcribe.return_value = ""

        app._process(np.zeros(100, dtype=np.float32))

        app.btn.paste_and_notify.emit.assert_not_called()
        app.btn.show_notification.assert_called_once()
        app.btn.reset_requested.emit.assert_called_once()

    def test_process_glm_fallback(self):
        app = self._make_app()
        app.asr.transcribe.return_value = "原始文本"
        app.processor.improve.side_effect = Exception("API error")

        app._process(np.zeros(100, dtype=np.float32))

        app.btn.paste_and_notify.emit.assert_called_once_with("原始文本")
        app.btn.show_notification.assert_called()

    def test_process_correction_disabled(self):
        app = self._make_app()
        app._correction_enabled = False
        app.asr.transcribe.return_value = "原始文本"

        app._process(np.zeros(100, dtype=np.float32))

        app.processor.improve.assert_not_called()
        app.btn.paste_and_notify.emit.assert_called_once_with("原始文本")

    def test_process_asr_failure(self):
        app = self._make_app()
        app.asr.transcribe.side_effect = Exception("model error")

        app._process(np.zeros(100, dtype=np.float32))

        app.btn.show_notification.assert_called()
        app.btn.reset_requested.emit.assert_called_once()

    def test_toggle_idle_to_recording(self):
        app = self._make_app()
        app.btn.state = "idle"
        with patch("app.winsound"):
            app.toggle()
        app.recorder.start.assert_called_once()
        app.btn.set_state.assert_called_once_with("recording")

    def test_toggle_recording_to_processing(self):
        app = self._make_app()
        app.btn.state = "recording"
        app.recorder.stop.return_value = np.zeros(16000, dtype=np.float32)
        with patch("app.winsound"):
            app.toggle()
        app.recorder.stop.assert_called_once()
        app.btn.set_state.assert_called_with("processing")

    def test_toggle_recording_too_short(self):
        app = self._make_app()
        app.btn.state = "recording"
        app.recorder.stop.return_value = None
        with patch("app.winsound"):
            app.toggle()
        app.btn.show_notification.assert_called_once_with("语音输入", "录音时间太短")

    def test_toggle_cancel_processing(self):
        app = self._make_app()
        app.btn.state = "processing"
        app.toggle()
        app.btn.set_state.assert_called_once_with("idle")
        app.btn.show_notification.assert_called_once_with("语音输入", "已取消处理")


class TestAutostart:
    def _make_app(self):
        app_module.VoiceInputApp.__init__ = lambda self: None
        app = app_module.VoiceInputApp.__new__(app_module.VoiceInputApp)
        app._autostart_enabled = False
        return app

    @patch("app.winreg")
    def test_read_autostart_true(self, mock_winreg):
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value = mock_key
        mock_winreg.QueryValueEx.return_value = ("some_path", mock_winreg.REG_SZ)

        app = self._make_app()
        result = app._read_autostart()

        assert result is True
        mock_winreg.OpenKey.assert_called_once()

    @patch("app.winreg")
    def test_read_autostart_false(self, mock_winreg):
        mock_winreg.OpenKey.side_effect = FileNotFoundError

        app = self._make_app()
        result = app._read_autostart()

        assert result is False

    @patch("app.winreg")
    def test_toggle_autostart_enable(self, mock_winreg):
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value = mock_key
        mock_winreg.HKEY_CURRENT_USER = winreg.HKEY_CURRENT_USER
        mock_winreg.KEY_SET_VALUE = winreg.KEY_SET_VALUE
        mock_winreg.REG_SZ = winreg.REG_SZ

        app = self._make_app()
        app._toggle_autostart(True)

        mock_winreg.SetValueEx.assert_called_once()
        assert app._autostart_enabled is True

    @patch("app.winreg")
    def test_toggle_autostart_disable(self, mock_winreg):
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value = mock_key
        mock_winreg.HKEY_CURRENT_USER = winreg.HKEY_CURRENT_USER
        mock_winreg.KEY_SET_VALUE = winreg.KEY_SET_VALUE

        app = self._make_app()
        app._autostart_enabled = True
        app._toggle_autostart(False)

        mock_winreg.DeleteValue.assert_called_once()
        assert app._autostart_enabled is False


class TestHotkey:
    def _make_mic(self):
        import ui as ui_module
        mic = ui_module.FloatingMic.__new__(ui_module.FloatingMic)
        mic._hotkey_name = "F8"
        mic._hotkey_vk = 0x77
        mic._settings = MagicMock()
        mic.winId = MagicMock(return_value=12345)
        mic.setToolTip = MagicMock()
        return mic

    @patch("ui.ctypes")
    def test_set_hotkey_registers_new_key(self, mock_ctypes):
        mic = self._make_mic()
        mic.set_hotkey("F6")
        assert mic._hotkey_name == "F6"
        assert mic._hotkey_vk == 0x75
        mock_ctypes.windll.user32.UnregisterHotKey.assert_called_once()
        mock_ctypes.windll.user32.RegisterHotKey.assert_called_once()

    @patch("ui.ctypes")
    def test_set_hotkey_noop_when_same(self, mock_ctypes):
        mic = self._make_mic()
        mic.set_hotkey("F8")
        mock_ctypes.windll.user32.UnregisterHotKey.assert_not_called()

    @patch("ui.ctypes")
    def test_set_hotkey_saves_to_settings(self, mock_ctypes):
        mic = self._make_mic()
        mic.set_hotkey("F12")
        mic._settings.setValue.assert_called_with("hotkey", "F12")
