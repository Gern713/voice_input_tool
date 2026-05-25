import logging

import numpy as np
from funasr import AutoModel

from config import HOTWORDS_FILE


def load_hotwords(path=HOTWORDS_FILE):
    try:
        with open(path, "r", encoding="utf-8") as f:
            words = [line.strip() for line in f if line.strip()]
        return " ".join(words)
    except FileNotFoundError:
        return ""


class ASRClient:
    def __init__(self):
        self.model = AutoModel(
            model="paraformer-zh",
            model_revision="v2.0.4",
            disable_update=True,
            trust_remote_code=True,
        )
        self._hotwords = load_hotwords()
        if self._hotwords:
            logging.info("热词已加载: %s", self._hotwords[:50])

    def transcribe(self, audio: np.ndarray) -> str:
        kwargs = dict(input=audio, batch_size_s=300)
        if self._hotwords:
            kwargs["hotword"] = self._hotwords
        result = self.model.generate(**kwargs)
        if result and result[0].get("text"):
            return result[0]["text"].strip()
        return ""
