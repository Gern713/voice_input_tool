import sys
import time
import pyperclip

IS_WINDOWS = sys.platform == "win32"


def _simulate_paste():
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


def paste_text(text: str):
    old = ""
    try:
        old = pyperclip.paste()
    except Exception:
        pass

    pyperclip.copy(text)
    time.sleep(0.05)
    _simulate_paste()
    time.sleep(0.1)

    try:
        pyperclip.copy(old)
    except Exception:
        pass
