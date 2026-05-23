import sys
import threading
import time
import ctypes

from PySide6.QtWidgets import QApplication, QWidget, QSystemTrayIcon, QMenu
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QPixmap, QIcon

import pyperclip

from config import ZHIPU_API_KEY
from recorder import AudioRecorder
from asr_client import ASRClient
from text_processor import TextProcessor

WM_HOTKEY = 0x0312


class FloatingMic(QWidget):
    clicked = Signal()
    reset_requested = Signal()
    paste_and_notify = Signal(str)

    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"

    def __init__(self):
        super().__init__()
        self.state = self.IDLE
        self._drag_start = None
        self._dragging = False
        self._pulse = 0
        self._target_hwnd = None
        self._hotkey_cb = None
        self._tick_count = 0

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(64, 84)
        self.setToolTip("点击录音 | 拖拽移动 | F8 快捷键")

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

        self._timeout_timer = QTimer(self)
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.timeout.connect(self._on_timeout)

        self.reset_requested.connect(self._do_reset)
        self.paste_and_notify.connect(self._do_paste_and_notify)

        ctypes.windll.user32.RegisterHotKey(int(self.winId()), 1, 0, 0x77)

        screen = QApplication.primaryScreen().geometry()
        self.move(screen.right() - 100, screen.center().y() - 32)

    def nativeEvent(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and msg.wParam == 1:
                if self._hotkey_cb:
                    self._hotkey_cb()
                return True, 0
        return False, 0

    def enterEvent(self, event):
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        my_hwnd = int(self.winId())
        if hwnd != my_hwnd and hwnd != 0:
            self._target_hwnd = hwnd

    def set_state(self, state):
        self.state = state
        if state == self.RECORDING:
            self._pulse = 0
            self._tick_count = 0
            self._timer.start(60)
        elif state == self.PROCESSING:
            self._timer.stop()
            self._timeout_timer.start(30000)
        else:
            self._timer.stop()
            self._timeout_timer.stop()
        self.update()

    def _do_reset(self):
        self.set_state(self.IDLE)

    def _do_paste_and_notify(self, text):
        target = self._target_hwnd
        self.hide()

        try:
            old_clip = pyperclip.paste()
        except Exception:
            old_clip = None

        if target:
            ctypes.windll.user32.SetForegroundWindow(target)
            time.sleep(0.1)

        pyperclip.copy(text)
        time.sleep(0.05)

        user32 = ctypes.windll.user32
        user32.keybd_event(0x11, 0, 0, 0)
        user32.keybd_event(0x56, 0, 0, 0)
        user32.keybd_event(0x56, 0, 2, 0)
        user32.keybd_event(0x11, 0, 2, 0)
        time.sleep(0.3)

        if old_clip is not None:
            try:
                pyperclip.copy(old_clip)
            except Exception:
                pass

        self.show()

        if hasattr(self, "_tray_ref") and self._tray_ref:
            self._tray_ref.showMessage(
                "语音输入", text, QSystemTrayIcon.MessageIcon.Information, 2000
            )

    def _on_timeout(self):
        print("处理超时，自动重置")
        self.set_state(self.IDLE)

    def _tick(self):
        self._pulse = (self._pulse + 1) % 20
        self._tick_count += 1
        self.update()

    # --- Drag & Click ---
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_start = e.globalPosition().toPoint() - self.pos()
            self._dragging = False

    def mouseMoveEvent(self, e):
        if self._drag_start is None:
            return
        new_pos = e.globalPosition().toPoint() - self._drag_start
        if not self._dragging:
            if (new_pos - self.pos()).manhattanLength() > 4:
                self._dragging = True
        if self._dragging:
            self.move(new_pos)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and not self._dragging:
            self.clicked.emit()
        self._drag_start = None

    # --- Paint ---
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        cx, cy, r = 32, 32, 30

        if self.state == self.RECORDING:
            secs = self._tick_count // 17
            p.setFont(QFont("Microsoft YaHei", 9))
            p.setPen(QColor(255, 255, 255))
            p.drawText(0, 68, 64, 16, Qt.AlignCenter, f"{secs}s")

        if self.state == self.IDLE:
            bg = QColor(74, 144, 217)
        elif self.state == self.RECORDING:
            alpha = 160 + int(95 * abs(self._pulse - 10) / 10)
            bg = QColor(220, 50, 50, min(alpha, 255))
        else:
            bg = QColor(240, 180, 40)

        p.setBrush(bg)
        p.setPen(Qt.NoPen)
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        white = QColor(255, 255, 255)

        if self.state == self.IDLE:
            self._draw_mic(p, cx, cy, white)
        elif self.state == self.RECORDING:
            self._draw_stop(p, cx, cy, white)
        else:
            self._draw_dots(p, cx, cy, white)

    def _draw_mic(self, p, cx, cy, color):
        p.setPen(QPen(color, 2.5))
        p.setBrush(color)
        p.drawRoundedRect(cx - 5, cy - 12, 10, 16, 5, 5)
        p.setBrush(Qt.NoBrush)
        p.drawArc(cx - 11, cy - 6, 22, 22, 35 * 16, 110 * 16)
        p.drawLine(cx, cy + 6, cx, cy + 10)
        p.drawLine(cx - 6, cy + 10, cx + 6, cy + 10)

    def _draw_stop(self, p, cx, cy, color):
        p.setBrush(color)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(cx - 8, cy - 8, 16, 16, 3, 3)

    def _draw_dots(self, p, cx, cy, color):
        p.setBrush(color)
        p.setPen(Qt.NoPen)
        for dx in [-9, 0, 9]:
            p.drawEllipse(cx + dx - 3, cy - 3, 6, 6)


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
            except Exception as e:
                print(f"录音启动失败: {e}")
        elif self.btn.state == FloatingMic.RECORDING:
            audio_data = self.recorder.stop()
            self.btn.set_state(FloatingMic.PROCESSING)
            if audio_data is not None:
                threading.Thread(
                    target=self._process, args=(audio_data,), daemon=True
                ).start()
            else:
                self.btn.set_state(FloatingMic.IDLE)

    def _process(self, audio_data):
        try:
            raw_text = self.asr.transcribe(audio_data)
            if not raw_text:
                print("未识别到语音内容")
                return

            print(f"ASR: {raw_text}")

            text = self.processor.improve(raw_text)
            print(f"GLM: {text}")

            self.btn.paste_and_notify.emit(text)
        except Exception as e:
            print(f"处理失败: {e}")
        finally:
            self.btn.reset_requested.emit()

    def run(self):
        return self.app.exec()


def main():
    if not ZHIPU_API_KEY:
        print("请先设置 ZHIPU_API_KEY（config.py 或环境变量）")
        print("获取: https://open.bigmodel.cn")
        sys.exit(1)

    print("语音输入助手启动中...")
    print("首次运行会加载 ASR 模型，请稍候")
    app = VoiceInputApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
