import sounddevice as sd
import numpy as np
import threading

from config import SAMPLE_RATE, CHANNELS


class AudioRecorder:
    def __init__(self):
        self.sr = SAMPLE_RATE
        self._frames = []
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        self._frames = []
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
