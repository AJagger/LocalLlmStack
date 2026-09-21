from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


VOICE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class VoiceConfigurationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class VoiceDefinition:
    id: str
    name: str
    audio_prompt: Path | None

    @property
    def builtin(self) -> bool:
        return self.audio_prompt is None


@dataclass(frozen=True, slots=True)
class VoiceCatalog:
    default_voice: str
    voices: dict[str, VoiceDefinition]

    def get(self, voice_id: str) -> VoiceDefinition:
        try:
            return self.voices[voice_id]
        except KeyError as exc:
            available = ", ".join(sorted(self.voices))
            raise VoiceConfigurationError(
                f"unknown voice '{voice_id}'; available voices: {available}"
            ) from exc


def _parse_voice(
    voice_id: str,
    raw: dict[str, Any],
    *,
    config_dir: Path,
) -> VoiceDefinition:
    if not VOICE_ID_PATTERN.fullmatch(voice_id):
        raise VoiceConfigurationError(
            f"invalid voice id '{voice_id}'; use lower-case letters, numbers, '-' or '_'"
        )

    name = str(raw.get("name") or voice_id).strip()
    source = raw.get("source", "builtin")

    if source in (None, "builtin"):
        return VoiceDefinition(id=voice_id, name=name, audio_prompt=None)

    source_path = Path(str(source))
    if not source_path.is_absolute():
        source_path = (config_dir / source_path).resolve()

    return VoiceDefinition(id=voice_id, name=name, audio_prompt=source_path)


def load_voice_catalog(config_path: Path, default_voice: str) -> VoiceCatalog:
    """Load configured voices, falling back to the model's built-in voice."""

    if not config_path.exists():
        fallback = VoiceDefinition(
            id=default_voice,
            name="Chatterbox built-in voice",
            audio_prompt=None,
        )
        return VoiceCatalog(default_voice=default_voice, voices={default_voice: fallback})

    with config_path.open("r", encoding="utf-8") as handle:
        raw_document = yaml.safe_load(handle) or {}

    if not isinstance(raw_document, dict):
        raise VoiceConfigurationError("voices configuration must contain a YAML mapping")

    raw_voices = raw_document.get("voices")
    if not isinstance(raw_voices, dict) or not raw_voices:
        raise VoiceConfigurationError("voices configuration must contain a non-empty 'voices' mapping")

    voices: dict[str, VoiceDefinition] = {}
    for voice_id, raw in raw_voices.items():
        if not isinstance(voice_id, str) or not isinstance(raw, dict):
            raise VoiceConfigurationError("each voice must be a mapping keyed by its string id")
        definition = _parse_voice(voice_id, raw, config_dir=config_path.parent)
        voices[definition.id] = definition

    configured_default = str(raw_document.get("default_voice") or default_voice)
    if configured_default not in voices:
        raise VoiceConfigurationError(
            f"default voice '{configured_default}' is not present in the voices mapping"
        )

    return VoiceCatalog(default_voice=configured_default, voices=voices)
