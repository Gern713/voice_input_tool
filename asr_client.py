import logging

import numpy as np
from funasr import AutoModel

from config import HOTWORDS_FILE
import dict_manager


def load_hotwords(path=HOTWORDS_FILE):
    return dict_manager.load_all_hotwords(path)


class ASRClient:
    def __init__(self):
        self.model = AutoModel(
            model="iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
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


class StreamingASRClient:
    def __init__(self):
        self.model = AutoModel(
            model="paraformer-zh-streaming",
            model_revision="v2.0.4",
            disable_update=True,
            trust_remote_code=True,
        )
        self._cache = {}
        self._chunk_size = [0, 10, 5]

    def reset(self):
        self._cache = {}

    def process_chunk(self, audio: np.ndarray, is_final=False) -> str:
        result = self.model.generate(
            input=audio,
            cache=self._cache,
            is_final=is_final,
            chunk_size=self._chunk_size,
            encoder_chunk_look_back=4,
            decoder_chunk_look_back=1,
        )
        if result and result[0].get("text"):
            return result[0]["text"].strip()
        return ""
