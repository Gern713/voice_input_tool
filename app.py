import sys
import os
import ctypes
import threading
import logging
import winreg
import winsound

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, QTimer, QAbstractNativeEventFilter
from PySide6.QtGui import QColor, QPixmap, QIcon, QPainter, QPen

from ui import FloatingMic
from recorder import AudioRecorder
from asr_client import ASRClient
from text_processor import TextProcessor
import history

WM_HOTKEY = 0x0312
_HOTKEY_ID = 1
_MOD_ALT = 0x0001
_MOD_NOREPEAT = 0x4000
_VK_V = 0x56


class _GlobalHotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, callback):
        super().__init__()
        self._cb = callback

    def nativeEventFilter(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and msg.wParam == _HOTKEY_ID:
                self._cb()
                return True
        return False

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
        self.btn.show()

        self._init_tray()
        self.btn._tray_ref = self.tray

        # Global hotkey (Alt+V)
        self._hotkey_filter = None
        ok = ctypes.windll.user32.RegisterHotKey(
            0, _HOTKEY_ID, _MOD_ALT | _MOD_NOREPEAT, _VK_V
        )
        if ok:
            self._hotkey_filter = _GlobalHotkeyFilter(self.toggle)
            self.app.installNativeEventFilter(self._hotkey_filter)
            logging.info("全局热键 Alt+V 已注册")
        else:
            logging.warning("Alt+V 热键注册失败（可能被其他程序占用）")

    def _toggle_visibility(self, checked):
        self.btn.setVisible(checked)
        logging.info("浮动按钮: %s", "显示" if checked else "隐藏")

    def _toggle_correction(self, checked):
        self._correction_enabled = checked
        logging.info("文本纠错: %s", "开启" if checked else "关闭")

    def _edit_hotwords(self):
        os.startfile("hotwords.txt")

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
        self._tray_menu = QMenu()
        self._tray_menu.aboutToShow.connect(self._rebuild_menu)
        self.tray.setContextMenu(self._tray_menu)
        self.tray.setToolTip("语音输入助手 - Alt+V 开始录音")
        self.tray.activated.connect(self._tray_click)
        self.tray.show()

    def _rebuild_menu(self):
        self._tray_menu.clear()
        self._populate_menu(self._tray_menu)

    def _populate_menu(self, menu):
        show_action = QAction("显示按钮", self.app)
        show_action.setCheckable(True)
        show_action.setChecked(self.btn.isVisible())
        show_action.triggered.connect(self._toggle_visibility)
        menu.addAction(show_action)

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

    def run(self):
        self.app.aboutToQuit.connect(self._cleanup)
        return self.app.exec()

    def _cleanup(self):
        if self._hotkey_filter:
            ctypes.windll.user32.UnregisterHotKey(0, _HOTKEY_ID)
