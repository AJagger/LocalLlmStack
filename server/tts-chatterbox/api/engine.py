from chatterbox.tts_turbo import ChatterboxTurboTTS


class ChatterboxEngine:
    def __init__(self, model_path: str) -> None:
        self.model_path = model_path
        self.model: ChatterboxTurboTTS | None = None

    def load(self) -> None:
        self.model = ChatterboxTurboTTS.from_local(
            self.model_path,
            device="cpu",
            nano=False,
        )

    def generate(self, text: str):
        if self.model is None:
            raise RuntimeError("The Chatterbox model has not been loaded")

        waveform = self.model.generate(text)
        return waveform, self.model.sr
