import numpy as np
from funasr import AutoModel


class ASRClient:
    def __init__(self):
        self.model = AutoModel(
            model="paraformer-zh",
            model_revision="v2.0.4",
            disable_update=True,
            trust_remote_code=True,
        )

    def transcribe(self, audio: np.ndarray) -> str:
        result = self.model.generate(input=audio, batch_size_s=300)
        if result and result[0].get("text"):
            return result[0]["text"].strip()
        return ""
