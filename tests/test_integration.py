import sys
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
