import sys
import time
import pyperclip

IS_WINDOWS = sys.platform == "win32"


def paste_text(text: str, target_hwnd=None):
    if IS_WINDOWS and target_hwnd:
        import ctypes
        ctypes.windll.user32.SetForegroundWindow(target_hwnd)
        time.sleep(0.05)

    pyperclip.copy(text)
    time.sleep(0.05)

    if IS_WINDOWS:
        import ctypes
        user32 = ctypes.windll.user32
        user32.keybd_event(0x11, 0, 0, 0)
        user32.keybd_event(0x56, 0, 0, 0)
        user32.keybd_event(0x56, 0, 2, 0)
        user32.keybd_event(0x11, 0, 2, 0)
    else:
        import subprocess
        subprocess.run(["xdotool", "key", "ctrl+v"])

    time.sleep(0.3)
