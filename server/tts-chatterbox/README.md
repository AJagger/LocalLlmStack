# Chatterbox TTS container starter

This directory contains the first implementation of the CPU-only Chatterbox
speech service planned for LocalLLMStack. It is intentionally isolated from the
main stack routing for now: it can be built and tested independently before the
router, LiteLLM and Open WebUI changes are added.

## What is implemented

- CPU-only Chatterbox Nano loading from a read-only local model directory.
- A single Uvicorn worker and a serial inference lock, preventing concurrent
  requests from changing Chatterbox's mutable voice conditionals.
- A bounded queue (`one active + CHATTERBOX_MAX_QUEUED_REQUESTS waiting`).
- OpenAI-style `POST /v1/audio/speech` with MP3 and WAV output.
- `GET /health`, `GET /health/ready`, `GET /v1/models`, and
  `GET /v1/audio/voices`.
- The model's built-in voice under the default id `alloy`.
- Optional administrator-managed voice presets from reference WAV files.
- Sentence-aware internal chunking and one joined output file.
- A pinned Nano model download script for offline provisioning.

This is an MVP. Join trimming/crossfading, louder audio normalisation,
end-to-end LiteLLM verification, and subjective voice tuning remain later work.

## Model layout

The container expects this runtime mount by default:

```text
/models/audio/tts/chatterbox-nano/
├── added_tokens.json
├── conds.pt
├── merges.txt
├── s3gen_meanflow.safetensors
├── special_tokens_map.json
├── t3_nano_v1.safetensors
├── tokenizer_config.json
├── ve.safetensors
└── vocab.json
```

Download those files on an internet-connected machine:

```bash
python -m pip install -r requirements-provisioning.txt
python scripts/download_model.py /path/to/models/audio/tts/chatterbox-nano
```

The script pins Nano revision
`71ccd1d0081b430592cea481f4307e764e07bc64` rather than downloading an
uncontrolled future `main` revision.

## Voices

Copy the example manifest and keep actual voice recordings outside source
control:

```bash
cp voices/voices.yaml.example voices/voices.yaml
```

The built-in `alloy` entry needs no recording. A custom entry points to a WAV
file containing more than five seconds of clean, dry English speech. Chatterbox
uses at most roughly ten seconds for conditioning.

```yaml
default_voice: alloy
voices:
  alloy:
    name: Chatterbox built-in voice
    source: builtin
  nova:
    name: Friendly bright voice
    source: ./nova.wav
```

Voice conditionals are prepared once during startup and reused. Requests are
serialised because the upstream model stores the selected conditionals on the
model object.

## Build

Run this directory as the Docker build context:

```bash
docker build -t local/chatterbox-tts:0.1.0 .
```

The build installs CPU-only PyTorch. It installs the official
`chatterbox-tts==0.1.7` package without its optional Gradio and multilingual UI
dependencies, then supplies the smaller English Turbo/Nano runtime dependency
set explicitly.

## Run in isolation

From this directory, set `MODEL_DIR` to the parent model directory used by the
main stack and use the example Compose file:

```bash
cp voices/voices.yaml.example voices/voices.yaml
MODEL_DIR=/path/to/models docker compose -f compose.example.yaml up --build
```

Check readiness:

```bash
curl http://127.0.0.1:8010/health/ready
```

Generate WAV:

```bash
curl http://127.0.0.1:8010/v1/audio/speech \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "speech",
    "input": "Hello. This is the first local Chatterbox Nano endpoint.",
    "voice": "alloy",
    "response_format": "wav"
  }' \
  --output speech.wav
```

Generate MP3 by changing `response_format` to `mp3`.

## Configuration

All settings use the `CHATTERBOX_` prefix. Important values are:

| Variable | Default | Purpose |
|---|---:|---|
| `CHATTERBOX_MODEL_VARIANT` | `nano` | `nano` now; `turbo` is supported by the wrapper when a Turbo checkpoint is mounted. |
| `CHATTERBOX_MODEL_PATH` | `/models/audio/tts/chatterbox-nano` | Local checkpoint directory. |
| `CHATTERBOX_VOICES_CONFIG` | `/voices/voices.yaml` | Voice manifest. A missing file falls back to the built-in voice. |
| `CHATTERBOX_DEFAULT_VOICE` | `alloy` | Built-in fallback voice id. |
| `CHATTERBOX_TORCH_NUM_THREADS` | `0` | `0` lets PyTorch choose; set explicitly after benchmarking. |
| `CHATTERBOX_MAX_INPUT_CHARS` | `6000` | Hard request-size guard. |
| `CHATTERBOX_MAX_CHUNK_CHARS` | `280` | Approximate maximum text passed to one generation call. |
| `CHATTERBOX_MAX_QUEUED_REQUESTS` | `2` | Waiting requests allowed behind the active inference. |
| `CHATTERBOX_ACCEPTED_MODEL_NAMES` | `speech,chatterbox,chatterbox-nano` | API model names accepted by the endpoint. |

`speed` is accepted for OpenAI request compatibility but values other than
`1.0` are rejected until a deliberate time-stretch implementation is added.

## Tests

The tests use a fake engine and do not download or load Chatterbox:

```bash
python -m pip install -r requirements-dev.txt
pytest -q
```

## Next integration step

After the image has been built and benchmarked on the target CPU, add it to the
main `server/compose.yaml` under an `audio` profile, mount the model and voices
read-only, then add internal-router port `8105` and the LiteLLM `speech` alias.
