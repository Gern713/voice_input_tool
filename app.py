import sys
import os
import queue
import threading
import logging
import winreg
import winsound

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap, QIcon, QPainter, QPen

from ui import FloatingMic, HOTKEY_OPTIONS
from recorder import AudioRecorder
from asr_client import ASRClient, StreamingASRClient
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
        self._streaming_asr = StreamingASRClient()
        self._chunk_queue = queue.Queue()

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

        hotwords_action = menu.addAction("编辑热词")
        hotwords_action.triggered.connect(self._edit_hotwords)

        hotkey_menu = menu.addMenu("快捷键")
        for name in HOTKEY_OPTIONS:
            action = hotkey_menu.addAction(name)
            action.setData(name)
            if name == self.btn._hotkey_name:
                font = action.font()
                font.setBold(True)
                action.setFont(font)
        hotkey_menu.triggered.connect(self._on_hotkey_change)

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

    def _edit_hotwords(self):
        os.startfile("hotwords.txt")

    def _on_hotkey_change(self, action):
        name = action.data()
        if name:
            self.btn.set_hotkey(name)
            self._refresh_tray_menu()

    def _on_chunk(self, audio_chunk):
        self._chunk_queue.put(audio_chunk)

    def _chunk_worker(self):
        while True:
            chunk = self._chunk_queue.get()
            if chunk is None:
                break
            try:
                text = self._streaming_asr.process_chunk(chunk)
                if text:
                    self.btn.partial_text.emit(text)
            except Exception as e:
                logging.warning("流式识别 chunk 失败: %s", e)

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
        p.setPen(Qt.NoPen)
        p.drawEllipse(2, 2, 28, 28)
        white = QColor(255, 255, 255)
        p.setBrush(white)
        p.drawRoundedRect(13, 6, 6, 11, 3, 3)
        p.setBrush(Qt.NoBrush)
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
                self._streaming_asr = StreamingASRClient()
                self._chunk_queue = queue.Queue()
                self.recorder.start(chunk_callback=self._on_chunk)
                threading.Thread(target=self._chunk_worker, daemon=True).start()
                self.btn.set_state(FloatingMic.RECORDING)
                winsound.Beep(800, 150)
            except Exception as e:
                logging.error("录音启动失败: %s", e)
        elif self.btn.state == FloatingMic.RECORDING:
            winsound.Beep(400, 200)
            audio_data = self.recorder.stop()
            self._chunk_queue.put(None)
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
            # Use offline ASR for final accurate transcription
            raw_text = self.asr.transcribe(audio_data)

            # If offline ASR fails, try streaming final as fallback
            if not raw_text:
                try:
                    raw_text = self._streaming_asr.end_session(audio_data[-9600:] if len(audio_data) > 9600 else audio_data)
                except Exception:
                    pass

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
