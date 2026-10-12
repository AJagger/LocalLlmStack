import threading
from chatterbox.tts_turbo import ChatterboxTurboTTS


class ChatterboxEngine:
    def __init__(self, model_path: str) -> None:
        self.model_path = model_path
        self.model: ChatterboxTurboTTS | None = None
        self._lock = threading.Lock()

    def load(self) -> None:
        self.model = ChatterboxTurboTTS.from_local(
            self.model_path,
            device="cpu",
        )

    def generate(self, text: str):
        if self.model is None:
            raise RuntimeError("The Chatterbox model has not been loaded")
        with self._lock:        
            waveform = self.model.generate(text)
            sr = self.model.sr
        return waveform, sr
