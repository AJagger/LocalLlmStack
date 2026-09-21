from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Protocol

import numpy as np

from .config import Settings
from .voices import VoiceCatalog, VoiceConfigurationError


LOGGER = logging.getLogger(__name__)


class EngineNotReadyError(RuntimeError):
    pass


class SpeechEngine(Protocol):
    sample_rate: int

    def load(self) -> None: ...

    def synthesize(self, text: str, voice_id: str) -> np.ndarray: ...


class ChatterboxEngine:
    """CPU-only wrapper around Chatterbox Nano/Turbo local checkpoints."""

    def __init__(self, settings: Settings, voices: VoiceCatalog) -> None:
        self._settings = settings
        self._voices = voices
        self._model = None
        self._torch = None
        self._conditionals: dict[str, object] = {}
        self.sample_rate = 24_000

    def _validate_model_files(self) -> None:
        model_path = self._settings.model_path
        variant_checkpoint = (
            "t3_nano_v1.safetensors"
            if self._settings.model_variant == "nano"
            else "t3_turbo_v1.safetensors"
        )
        required = {
            "ve.safetensors",
            "s3gen_meanflow.safetensors",
            variant_checkpoint,
            "tokenizer_config.json",
            "special_tokens_map.json",
            "added_tokens.json",
            "vocab.json",
            "merges.txt",
        }
        missing = sorted(name for name in required if not (model_path / name).is_file())
        if missing:
            raise FileNotFoundError(
                f"model directory '{model_path}' is missing: {', '.join(missing)}"
            )

    def _configure_torch(self, torch_module: object) -> None:
        if self._settings.torch_num_threads > 0:
            torch_module.set_num_threads(self._settings.torch_num_threads)
        try:
            torch_module.set_num_interop_threads(self._settings.torch_num_interop_threads)
        except RuntimeError:
            LOGGER.warning("PyTorch inter-op thread count was already initialised; leaving it unchanged")

    def load(self) -> None:
        self._validate_model_files()

        import torch
        from chatterbox.tts_turbo import ChatterboxTurboTTS

        self._configure_torch(torch)
        LOGGER.info(
            "Loading Chatterbox %s from %s on CPU",
            self._settings.model_variant,
            self._settings.model_path,
        )
        model = ChatterboxTurboTTS.from_local(
            self._settings.model_path,
            device=self._settings.device,
            nano=self._settings.model_variant == "nano",
        )

        if model.conds is not None:
            built_in_conditionals = copy.deepcopy(model.conds)
        else:
            built_in_conditionals = None

        conditionals: dict[str, object] = {}
        for voice_id, voice in self._voices.voices.items():
            if voice.builtin:
                if built_in_conditionals is None:
                    raise VoiceConfigurationError(
                        f"voice '{voice_id}' uses the built-in voice, but the model has no conds.pt"
                    )
                conditionals[voice_id] = copy.deepcopy(built_in_conditionals)
                continue

            prompt_path = Path(voice.audio_prompt)
            if not prompt_path.is_file():
                raise FileNotFoundError(
                    f"audio prompt for voice '{voice_id}' does not exist: {prompt_path}"
                )
            LOGGER.info("Preparing voice '%s' from %s", voice_id, prompt_path)
            model.prepare_conditionals(prompt_path)
            conditionals[voice_id] = copy.deepcopy(model.conds)

        self._torch = torch
        self._model = model
        self._conditionals = conditionals
        self.sample_rate = int(model.sr)
        LOGGER.info(
            "Chatterbox %s ready with %d voice(s) at %d Hz",
            self._settings.model_variant,
            len(conditionals),
            self.sample_rate,
        )

    def synthesize(self, text: str, voice_id: str) -> np.ndarray:
        if self._model is None or self._torch is None:
            raise EngineNotReadyError("Chatterbox model is not loaded")

        try:
            conditionals = self._conditionals[voice_id]
        except KeyError as exc:
            raise VoiceConfigurationError(f"voice '{voice_id}' was not prepared") from exc

        self._model.conds = conditionals
        with self._torch.inference_mode():
            waveform = self._model.generate(
                text,
                temperature=self._settings.temperature,
                top_p=self._settings.top_p,
                top_k=self._settings.top_k,
                repetition_penalty=self._settings.repetition_penalty,
            )

        return (
            waveform.squeeze()
            .detach()
            .to(device="cpu", dtype=self._torch.float32)
            .numpy()
            .astype(np.float32, copy=False)
        )
