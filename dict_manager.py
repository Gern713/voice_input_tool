import os
import logging
import urllib.request
from pathlib import Path

from PySide6.QtCore import QSettings

DICTS_DIR = Path.home() / ".voice_input_dicts"
_DICT_REGISTRY = {
    "medical": "医疗健康",
    "legal": "法律文书",
    "tech": "互联网科技",
    "finance": "金融财经",
    "gaming": "游戏电竞",
}

_BASE_URL = "https://raw.githubusercontent.com/Gern713/voice_input_tool/main/dicts"


def _settings():
    return QSettings("VoiceInput", "VoiceInput")


def get_available_dicts():
    enabled = _settings().value("enabled_dicts", [])
    if isinstance(enabled, str):
        enabled = [enabled]
    result = []
    for key, name in _DICT_REGISTRY.items():
        result.append({"key": key, "name": name, "enabled": key in enabled})
    return result


def toggle_dict(key, enabled):
    s = _settings()
    current = s.value("enabled_dicts", [])
    if isinstance(current, str):
        current = [current]
    if enabled:
        if key not in current:
            current.append(key)
            _download_dict(key)
    else:
        current = [k for k in current if k != key]
    s.setValue("enabled_dicts", current)


def _download_dict(key):
    DICTS_DIR.mkdir(parents=True, exist_ok=True)
    dest = DICTS_DIR / f"{key}.txt"
    if dest.exists():
        return
    url = f"{_BASE_URL}/{key}.txt"
    try:
        logging.info("下载词库: %s", key)
        urllib.request.urlretrieve(url, dest)
        logging.info("词库下载完成: %s", dest)
    except Exception as e:
        logging.warning("词库下载失败 %s: %s", key, e)


def _load_dict_file(path):
    try:
        return [line.strip() for line in open(path, encoding="utf-8") if line.strip()]
    except Exception:
        return []


def load_all_hotwords(hotwords_path=None):
    words = []
    if hotwords_path:
        words.extend(_load_dict_file(hotwords_path))
    enabled = _settings().value("enabled_dicts", [])
    if isinstance(enabled, str):
        enabled = [enabled]
    for key in enabled:
        cached = DICTS_DIR / f"{key}.txt"
        if cached.exists():
            words.extend(_load_dict_file(cached))
    return " ".join(words)
