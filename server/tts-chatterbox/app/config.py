from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from CHATTERBOX_* environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="CHATTERBOX_",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=(),
    )

    service_name: str = "chatterbox-tts"
    model_variant: Literal["nano", "turbo"] = "nano"
    model_path: Path = Path("/models/audio/tts/chatterbox-nano")
    device: Literal["cpu"] = "cpu"

    voices_config: Path = Path("/voices/voices.yaml")
    default_voice: str = "alloy"

    accepted_model_names: str = "speech,chatterbox,chatterbox-nano"
    max_input_chars: int = Field(default=6_000, ge=1, le=50_000)
    max_chunk_chars: int = Field(default=280, ge=80, le=2_000)
    pause_between_chunks_ms: int = Field(default=140, ge=0, le=2_000)
    max_queued_requests: int = Field(default=2, ge=0, le=100)

    torch_num_threads: int = Field(default=0, ge=0)
    torch_num_interop_threads: int = Field(default=1, ge=1)

    temperature: float = Field(default=0.8, gt=0.0, le=2.0)
    top_p: float = Field(default=0.95, gt=0.0, le=1.0)
    top_k: int = Field(default=1_000, ge=1)
    repetition_penalty: float = Field(default=1.2, ge=1.0, le=3.0)

    mp3_bitrate: str = "128k"
    ffmpeg_timeout_seconds: int = Field(default=120, ge=1, le=3_600)

    @field_validator("accepted_model_names")
    @classmethod
    def validate_model_names(cls, value: str) -> str:
        names = [item.strip() for item in value.split(",") if item.strip()]
        if not names:
            raise ValueError("at least one accepted model name is required")
        return ",".join(dict.fromkeys(names))

    @property
    def accepted_models(self) -> frozenset[str]:
        return frozenset(item.strip() for item in self.accepted_model_names.split(","))
