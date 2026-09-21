from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResponseFormat(StrEnum):
    MP3 = "mp3"
    WAV = "wav"


class SpeechRequest(BaseModel):
    """Subset of the OpenAI speech request supported by this service."""

    model_config = ConfigDict(extra="forbid")

    model: str = Field(min_length=1, max_length=128)
    input: str = Field(min_length=1)
    voice: str = Field(default="alloy", min_length=1, max_length=64)
    response_format: ResponseFormat = ResponseFormat.MP3
    speed: float = Field(default=1.0, ge=0.25, le=4.0)

    @field_validator("input")
    @classmethod
    def reject_blank_input(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("input must contain non-whitespace text")
        return value


class VoiceResponse(BaseModel):
    id: str
    name: str
    builtin: bool


class VoicesResponse(BaseModel):
    object: str = "list"
    data: list[VoiceResponse]
