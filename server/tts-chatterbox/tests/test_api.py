from __future__ import annotations

from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.voices import VoiceCatalog


class FakeEngine:
    sample_rate = 24_000

    def __init__(self, _settings: Settings, _voices: VoiceCatalog) -> None:
        self.loaded = False

    def load(self) -> None:
        self.loaded = True

    def synthesize(self, _text: str, _voice_id: str) -> np.ndarray:
        duration_seconds = 0.05
        samples = round(self.sample_rate * duration_seconds)
        return np.zeros(samples, dtype=np.float32)


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        model_path=tmp_path / "unused-model",
        voices_config=tmp_path / "missing-voices.yaml",
        max_chunk_chars=100,
    )


def test_health_and_readiness(tmp_path: Path) -> None:
    app = create_app(settings=make_settings(tmp_path), engine_factory=FakeEngine)

    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        ready = client.get("/health/ready")
        assert ready.status_code == 200
        assert ready.json()["status"] == "ready"


def test_wav_speech_response(tmp_path: Path) -> None:
    app = create_app(settings=make_settings(tmp_path), engine_factory=FakeEngine)

    with TestClient(app) as client:
        response = client.post(
            "/v1/audio/speech",
            json={
                "model": "speech",
                "input": "Hello from the local speech service.",
                "voice": "alloy",
                "response_format": "wav",
            },
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")
    assert response.content.startswith(b"RIFF")


def test_mp3_speech_response(tmp_path: Path) -> None:
    app = create_app(settings=make_settings(tmp_path), engine_factory=FakeEngine)

    with TestClient(app) as client:
        response = client.post(
            "/v1/audio/speech",
            json={
                "model": "speech",
                "input": "Hello from the local speech service.",
                "voice": "alloy",
                "response_format": "mp3",
            },
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/mpeg")
    assert len(response.content) > 100


def test_unknown_voice_returns_400(tmp_path: Path) -> None:
    app = create_app(settings=make_settings(tmp_path), engine_factory=FakeEngine)

    with TestClient(app) as client:
        response = client.post(
            "/v1/audio/speech",
            json={"model": "speech", "input": "Hello", "voice": "missing"},
        )

    assert response.status_code == 400
    assert "unknown voice" in response.json()["detail"]


def test_non_default_speed_is_rejected(tmp_path: Path) -> None:
    app = create_app(settings=make_settings(tmp_path), engine_factory=FakeEngine)

    with TestClient(app) as client:
        response = client.post(
            "/v1/audio/speech",
            json={"model": "speech", "input": "Hello", "speed": 1.25},
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "speed is not supported yet; use 1.0"
