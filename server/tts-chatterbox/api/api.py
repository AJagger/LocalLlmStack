from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from pydantic import BaseModel

from .audio import to_wav_bytes
from .config import MODEL_PATH
from .engine import ChatterboxEngine

engine = ChatterboxEngine(MODEL_PATH)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Loading happens before Uvicorn starts accepting requests. If model loading
    # fails, the container exits instead of running a broken API.
    engine.load()
    yield


app = FastAPI(title="Chatterbox Turbo Demo", lifespan=lifespan)


class SpeechRequest(BaseModel):
    input: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/ready")
def readiness():
    # The application only starts after engine.load() succeeds, so a running
    # endpoint is also a ready endpoint in this deliberately small demo.
    return {"status": "ready"}


@app.post("/v1/audio/speech")
def speech(request: SpeechRequest):
    waveform, sample_rate = engine.generate(request.input)
    audio = to_wav_bytes(waveform, sample_rate)
    return Response(content=audio, media_type="audio/wav")
