from __future__ import annotations

import io
import subprocess
from dataclasses import dataclass

import numpy as np
import soundfile as sf


class AudioEncodingError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class EncodedAudio:
    data: bytes
    media_type: str
    file_extension: str


def normalize_samples(samples: np.ndarray) -> np.ndarray:
    audio = np.asarray(samples, dtype=np.float32).reshape(-1)
    if audio.size == 0:
        raise AudioEncodingError("model returned empty audio")
    if not np.isfinite(audio).all():
        raise AudioEncodingError("model returned non-finite audio samples")
    return np.clip(audio, -1.0, 1.0)


def encode_wav(samples: np.ndarray, sample_rate: int) -> EncodedAudio:
    audio = normalize_samples(samples)
    buffer = io.BytesIO()
    sf.write(buffer, audio, sample_rate, format="WAV", subtype="PCM_16")
    return EncodedAudio(
        data=buffer.getvalue(),
        media_type="audio/wav",
        file_extension="wav",
    )


def encode_mp3(
    samples: np.ndarray,
    sample_rate: int,
    *,
    bitrate: str,
    timeout_seconds: int,
) -> EncodedAudio:
    audio = normalize_samples(samples).astype("<f4", copy=False)
    command = [
        "ffmpeg",
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "f32le",
        "-ar",
        str(sample_rate),
        "-ac",
        "1",
        "-i",
        "pipe:0",
        "-codec:a",
        "libmp3lame",
        "-b:a",
        bitrate,
        "-f",
        "mp3",
        "pipe:1",
    ]

    try:
        result = subprocess.run(
            command,
            input=audio.tobytes(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        raise AudioEncodingError("ffmpeg is not installed in the container") from exc
    except subprocess.TimeoutExpired as exc:
        raise AudioEncodingError("ffmpeg timed out while encoding MP3") from exc

    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise AudioEncodingError(f"ffmpeg failed to encode MP3: {error}")
    if not result.stdout:
        raise AudioEncodingError("ffmpeg returned an empty MP3")

    return EncodedAudio(
        data=result.stdout,
        media_type="audio/mpeg",
        file_extension="mp3",
    )
