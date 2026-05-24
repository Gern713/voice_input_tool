import sys
import os
import threading
import logging
import winreg
import winsound

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QColor, QPixmap, QIcon, QIcon, QPainter, QPen

from ui import FloatingMic
from recorder import AudioRecorder
from asr_client import ASRClient
from text_processor import TextProcessor
import history

AUTOSTART_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_NAME = "VoiceInputTool"


class VoiceInputApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.recorder = AudioRecorder()
        self.asr = ASRClient()
        self.processor = TextProcessor()

        self._correction_enabled = True
        self._autostart_enabled = self._read_autostart()

        self.btn = FloatingMic()
        self.btn.clicked.connect(self.toggle)
        self.btn._hotkey_cb = self.toggle
        self.btn.show()

        self._init_tray()
        self.btn._tray_ref = self.tray

    def _build_menu(self):
        menu = QMenu()

        autostart_action = QAction("开机自启", self.app)
        autostart_action.setCheckable(True)
        autostart_action.setChecked(self._autostart_enabled)
        autostart_action.triggered.connect(self._toggle_autostart)
        menu.addAction(autostart_action)

        correction_action = QAction("文本纠错", self.app)
        correction_action.setCheckable(True)
        correction_action.setChecked(self._correction_enabled)
        correction_action.triggered.connect(self._toggle_correction)
        menu.addAction(correction_action)

        hist = history.load()
        if hist:
            hist_menu = menu.addMenu("历史记录")
            for item in reversed(hist[-10:]):
                text = item["text"][:20] + ("..." if len(item["text"]) > 20 else "")
                action = hist_menu.addAction(text)
                action.setData(item["text"])
            hist_menu.triggered.connect(self._on_history_click)

        menu.addSeparator()
        menu.addAction("退出").triggered.connect(self.app.quit)
        return menu

    def _toggle_correction(self, checked):
        self._correction_enabled = checked
        logging.info("文本纠错: %s", "开启" if checked else "关闭")

    def _read_autostart(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, AUTOSTART_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            return False
        except Exception:
            return False

    def _toggle_autostart(self, checked):
        if checked:
            exe_path = os.path.abspath(sys.argv[0])
            cmd = f'"{sys.executable}" "{exe_path}"'
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, AUTOSTART_NAME, 0, winreg.REG_SZ, cmd)
                winreg.CloseKey(key)
                self._autostart_enabled = True
                logging.info("开机自启: 已开启")
            except Exception as e:
                logging.error("设置开机自启失败: %s", e)
                self._autostart_enabled = False
        else:
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_SET_VALUE)
                winreg.DeleteValue(key, AUTOSTART_NAME)
                winreg.CloseKey(key)
                self._autostart_enabled = False
                logging.info("开机自启: 已关闭")
            except FileNotFoundError:
                self._autostart_enabled = False
            except Exception as e:
                logging.error("取消开机自启失败: %s", e)

    def _on_history_click(self, action):
        text = action.data()
        if text:
            history.add(text)
            self.btn.paste_and_notify.emit(text)

    def _init_tray(self):
        pm = QPixmap(32, 32)
        pm.fill(QColor(0, 0, 0, 0))
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(74, 144, 217))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(2, 2, 28, 28)
        white = QColor(255, 255, 255)
        p.setBrush(white)
        p.drawRoundedRect(13, 6, 6, 11, 3, 3)
        p.setBrush(Qt.PenStyle.NoBrush)
        p.setPen(QPen(white, 2))
        p.drawArc(9, 12, 14, 14, 35 * 16, 110 * 16)
        p.drawLine(16, 19, 16, 23)
        p.drawLine(12, 23, 20, 23)
        p.end()
        icon = QIcon(pm)

        self.tray = QSystemTrayIcon(icon)
        self.tray.setContextMenu(self._build_menu())
        self.tray.setToolTip("语音输入助手 - 点击按钮开始录音")
        self.tray.activated.connect(self._tray_click)
        self.tray.show()

    def _refresh_tray_menu(self):
        self.tray.setContextMenu(self._build_menu())

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

    def _process(self, audio_data):
        try:
            raw_text = self.asr.transcribe(audio_data)
            if not raw_text:
                logging.info("未识别到语音内容")
                self.btn.show_notification("语音输入", "未识别到语音内容")
                return

            logging.info("ASR: %s", raw_text)

            if self._correction_enabled:
                try:
                    text = self.processor.improve(raw_text)
                    logging.info("GLM: %s", text)
                except Exception as e:
                    text = raw_text
                    logging.warning("GLM 纠错失败，使用原始文本: %s", e)
                    self.btn.show_notification("语音输入", "文本已输入（纠错失败）")
            else:
                text = raw_text

            history.add(text)
            self.btn.paste_and_notify.emit(text)
        except Exception as e:
            logging.error("处理失败: %s", e)
            self.btn.show_notification("语音输入", "处理失败，请重试")
        finally:
            self.btn.reset_requested.emit()
            self._refresh_tray_menu()

    def run(self):
        return self.app.exec()
