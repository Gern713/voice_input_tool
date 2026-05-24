import json
import logging
from pathlib import Path

MAX_ITEMS = 10
HISTORY_FILE = Path.home() / ".voice_input_history.json"


def load():
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save(items):
    HISTORY_FILE.write_text(
        json.dumps(items[-MAX_ITEMS:], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def add(text):
    items = load()
    items.append({"text": text})
    save(items)
    logging.info("历史记录已保存（共 %d 条）", len(items))
