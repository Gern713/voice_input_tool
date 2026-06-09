import sounddevice as sd
import numpy as np
import threading

from config import SAMPLE_RATE, CHANNELS

CHUNK_SAMPLES = 9600  # 600ms at 16kHz


class AudioRecorder:
    def __init__(self):
        self.sr = SAMPLE_RATE
        self._frames = []
        self._stop_event = threading.Event()
        self._thread = None
        self._chunk_cb = None
        self._chunk_buf = []
        self._chunk_count = 0

    def set_chunk_callback(self, cb):
        self._chunk_cb = cb

    def start(self):
        self._frames = []
        self._chunk_buf = []
        self._chunk_count = 0
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        with sd.InputStream(
            samplerate=self.sr,
            channels=CHANNELS,
            dtype="int16",
            blocksize=1024,
            callback=self._callback,
        ):
            self._stop_event.wait()

    def _callback(self, indata, frames, time_info, status):
        self._frames.append(indata.copy())
        if self._chunk_cb:
            self._chunk_buf.append(indata.copy())
            self._chunk_count += len(indata)
            if self._chunk_count >= CHUNK_SAMPLES:
                chunk = np.concatenate(self._chunk_buf).flatten().astype(np.float32)
                self._chunk_buf = []
                self._chunk_count = 0
                try:
                    self._chunk_cb(chunk)
                except Exception:
                    pass

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

        if not self._frames:
            return None

        audio = np.concatenate(self._frames)
        if len(audio) < self.sr * 0.3:
            return None

        return audio.flatten().astype(np.float32)
