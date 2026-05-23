import sys
import threading
import logging
import winsound

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QColor, QPixmap, QIcon

from ui import FloatingMic
from recorder import AudioRecorder
from asr_client import ASRClient
from text_processor import TextProcessor


class VoiceInputApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.recorder = AudioRecorder()
        self.asr = ASRClient()
        self.processor = TextProcessor()

        self.btn = FloatingMic()
        self.btn.clicked.connect(self.toggle)
        self.btn._hotkey_cb = self.toggle
        self.btn.show()

        self._init_tray()
        self.btn._tray_ref = self.tray

    def _init_tray(self):
        pm = QPixmap(32, 32)
        pm.fill(QColor(74, 144, 217))
        icon = QIcon(pm)

        menu = QMenu()
        menu.addAction("退出").triggered.connect(self.app.quit)

        self.tray = QSystemTrayIcon(icon)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip("语音输入助手 - 点击按钮开始录音")
        self.tray.activated.connect(self._tray_click)
        self.tray.show()

    def _tray_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle()

    def toggle(self):
        if self.btn.state == FloatingMic.IDLE:
            try:
                self.recorder.start()
                self.btn.set_state(FloatingMic.RECORDING)
                winsound.Beep(800, 150)
            except Exception as e:
                logging.error("录音启动失败: %s", e)
        elif self.btn.state == FloatingMic.RECORDING:
            winsound.Beep(400, 200)
            audio_data = self.recorder.stop()
            self.btn.set_state(FloatingMic.PROCESSING)
            if audio_data is not None:
                threading.Thread(
                    target=self._process, args=(audio_data,), daemon=True
                ).start()
            else:
                self.btn.set_state(FloatingMic.IDLE)
                self.btn.show_notification("语音输入", "录音时间太短")
        elif self.btn.state == FloatingMic.PROCESSING:
            self.btn.set_state(FloatingMic.IDLE)
            self.btn.show_notification("语音输入", "已取消处理")
            if audio_data is not None:
                threading.Thread(
                    target=self._process, args=(audio_data,), daemon=True
                ).start()
            else:
                self.btn.set_state(FloatingMic.IDLE)
                self.btn.show_notification("语音输入", "录音时间太短")

    def _process(self, audio_data):
        try:
            raw_text = self.asr.transcribe(audio_data)
            if not raw_text:
                logging.info("未识别到语音内容")
                self.btn.show_notification("语音输入", "未识别到语音内容")
                return

            logging.info("ASR: %s", raw_text)

            try:
                text = self.processor.improve(raw_text)
                logging.info("GLM: %s", text)
            except Exception as e:
                text = raw_text
                logging.warning("GLM 纠错失败，使用原始文本: %s", e)
                self.btn.show_notification("语音输入", "文本已输入（纠错失败）")

            self.btn.paste_and_notify.emit(text)
        except Exception as e:
            logging.error("处理失败: %s", e)
            self.btn.show_notification("语音输入", "处理失败，请重试")
        finally:
            self.btn.reset_requested.emit()

    def run(self):
        return self.app.exec()
