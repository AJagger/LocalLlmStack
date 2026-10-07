import io
import wave

import numpy as np
import torch


def to_wav_bytes(waveform: torch.Tensor, sample_rate: int) -> bytes:
    samples = waveform.detach().cpu().float().reshape(-1)
    samples = samples.clamp(-1.0, 1.0).numpy()
    pcm = (samples * 32767).astype(np.int16).tobytes()

    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm)

    return output.getvalue()
