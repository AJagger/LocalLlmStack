import os

MODEL_PATH = os.getenv("CHATTERBOX_MODEL_PATH", "/models/chatterbox-turbo")
HOST = os.getenv("TTS_HOST", "0.0.0.0")
PORT = int(os.getenv("TTS_PORT", "8000"))
