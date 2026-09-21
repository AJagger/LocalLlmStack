from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from time import monotonic

import numpy as np

from .chunking import split_text
from .config import Settings
from .engine import SpeechEngine


LOGGER = logging.getLogger(__name__)


class QueueFullError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class SynthesisResult:
    samples: np.ndarray
    sample_rate: int
    chunks: int
    elapsed_seconds: float


class SpeechService:
    def __init__(self, settings: Settings, engine: SpeechEngine) -> None:
        self._settings = settings
        self._engine = engine
        self._inference_lock = asyncio.Lock()
        self._queue_guard = asyncio.Lock()
        self._pending_requests = 0
        self._ready = False
        self._load_error: str | None = None

    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def load_error(self) -> str | None:
        return self._load_error

    def load(self) -> None:
        try:
            self._engine.load()
        except Exception as exc:
            self._ready = False
            self._load_error = f"{type(exc).__name__}: {exc}"
            raise
        else:
            self._load_error = None
            self._ready = True

    async def synthesize(self, text: str, voice_id: str) -> SynthesisResult:
        max_pending = self._settings.max_queued_requests + 1
        async with self._queue_guard:
            if self._pending_requests >= max_pending:
                raise QueueFullError(
                    f"TTS queue is full ({self._settings.max_queued_requests} queued request(s))"
                )
            self._pending_requests += 1

        started = monotonic()
        try:
            async with self._inference_lock:
                chunks = split_text(text, self._settings.max_chunk_chars)
                if not chunks:
                    raise ValueError("no text remained after normalisation")

                generated: list[np.ndarray] = []
                for index, chunk in enumerate(chunks):
                    LOGGER.info(
                        "Synthesising chunk %d/%d (%d characters) with voice '%s'",
                        index + 1,
                        len(chunks),
                        len(chunk),
                        voice_id,
                    )
                    samples = await asyncio.to_thread(
                        self._engine.synthesize,
                        chunk,
                        voice_id,
                    )
                    generated.append(np.asarray(samples, dtype=np.float32).reshape(-1))

                pause_samples = round(
                    self._engine.sample_rate
                    * self._settings.pause_between_chunks_ms
                    / 1_000
                )
                if pause_samples > 0 and len(generated) > 1:
                    pause = np.zeros(pause_samples, dtype=np.float32)
                    joined: list[np.ndarray] = []
                    for index, chunk_audio in enumerate(generated):
                        if index:
                            joined.append(pause)
                        joined.append(chunk_audio)
                    output = np.concatenate(joined)
                else:
                    output = np.concatenate(generated)

                return SynthesisResult(
                    samples=output,
                    sample_rate=self._engine.sample_rate,
                    chunks=len(chunks),
                    elapsed_seconds=monotonic() - started,
                )
        finally:
            async with self._queue_guard:
                self._pending_requests -= 1
