import time
import ctypes
import logging

from PySide6.QtWidgets import QApplication, QWidget, QSystemTrayIcon
from PySide6.QtCore import Qt, Signal, QTimer, QSettings
from PySide6.QtGui import QPainter, QColor, QPen, QFont

import pyperclip

# Win32 constants
WM_HOTKEY = 0x0312
VK_F8 = 0x77
VK_CTRL = 0x11
VK_V = 0x56
KEY_DOWN = 0
KEY_UP = 2

# Widget layout
BTN_WIDTH = 64
BTN_HEIGHT = 84
BTN_CIRCLE_R = 30
DRAG_THRESHOLD = 4

# Timing (ms)
PULSE_INTERVAL = 60
TICKS_PER_SEC = 17
PROCESSING_TIMEOUT = 30000

# Paste timing (s)
FOCUS_WAIT = 0.1
CLIPBOARD_WAIT = 0.05
PASTE_WAIT = 0.3


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
        self.setFixedSize(BTN_WIDTH, BTN_HEIGHT)
        self.setToolTip("点击录音 | 拖拽移动 | F8 快捷键")

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

        self._timeout_timer = QTimer(self)
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.timeout.connect(self._on_timeout)

        self._restore_timer = QTimer(self)
        self._restore_timer.setSingleShot(True)
        self._restore_timer.timeout.connect(self._do_restore_clipboard)
        self._pending_clip_restore = None

        self.reset_requested.connect(self._do_reset)
        self.paste_and_notify.connect(self._do_paste_and_notify)

        ctypes.windll.user32.RegisterHotKey(int(self.winId()), 1, 0, VK_F8)

        self._settings = QSettings("VoiceInput", "VoiceInput")
        saved_pos = self._settings.value("button_pos")
        if saved_pos:
            self.move(saved_pos)
        else:
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
            self._timer.start(PULSE_INTERVAL)
        elif state == self.PROCESSING:
            self._timer.stop()
            self._timeout_timer.start(PROCESSING_TIMEOUT)
        else:
            self._timer.stop()
            self._timeout_timer.stop()
        self.update()

    def _do_reset(self):
        self.set_state(self.IDLE)

    def show_notification(self, title, message, icon=QSystemTrayIcon.MessageIcon.Information):
        if hasattr(self, "_tray_ref") and self._tray_ref:
            self._tray_ref.showMessage(title, message, icon, 2000)

    def _do_paste_and_notify(self, text):
        target = self._target_hwnd
        self.hide()

        self._restore_timer.stop()
        self._pending_clip_restore = None

        try:
            old_clip = pyperclip.paste()
        except Exception:
            old_clip = None

        if target:
            ctypes.windll.user32.SetForegroundWindow(target)
            time.sleep(FOCUS_WAIT)

        pyperclip.copy(text)
        time.sleep(CLIPBOARD_WAIT)

        user32 = ctypes.windll.user32
        user32.keybd_event(VK_CTRL, 0, KEY_DOWN, 0)
        user32.keybd_event(VK_V, 0, KEY_DOWN, 0)
        user32.keybd_event(VK_V, 0, KEY_UP, 0)
        user32.keybd_event(VK_CTRL, 0, KEY_UP, 0)

        self.show()

        if old_clip is not None:
            self._pending_clip_restore = old_clip
            self._restore_timer.start(1500)

        if hasattr(self, "_tray_ref") and self._tray_ref:
            self._tray_ref.showMessage(
                "语音输入", text, QSystemTrayIcon.MessageIcon.Information, 2000
            )

    def _do_restore_clipboard(self):
        text = self._pending_clip_restore
        self._pending_clip_restore = None
        if text is not None:
            try:
                pyperclip.copy(text)
            except Exception:
                pass

    def _on_max_recording(self):
        logging.info("录音达到最大时长，自动停止")
        if self._hotkey_cb:
            self._hotkey_cb()

    def _on_timeout(self):
        logging.warning("处理超时，自动重置")
        self.set_state(self.IDLE)
        if hasattr(self, "_tray_ref") and self._tray_ref:
            self._tray_ref.showMessage(
                "语音输入", "处理超时，请重试",
                QSystemTrayIcon.MessageIcon.Warning, 2000
            )

    def _tick(self):
        self._pulse = (self._pulse + 1) % 20
        self._tick_count += 1
        if self._tick_count >= 60 * TICKS_PER_SEC:
            self._on_max_recording()
            return
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
            if (new_pos - self.pos()).manhattanLength() > DRAG_THRESHOLD:
                self._dragging = True
        if self._dragging:
            self.move(new_pos)
            self._settings.setValue("button_pos", new_pos)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and not self._dragging:
            self.clicked.emit()
        self._drag_start = None

    # --- Paint ---
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        cx, cy, r = 32, 32, BTN_CIRCLE_R

        if self.state == self.RECORDING:
            secs = self._tick_count // TICKS_PER_SEC
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
