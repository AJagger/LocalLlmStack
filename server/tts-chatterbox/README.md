# Minimal Chatterbox Turbo API demo

This is deliberately limited to the smallest useful proof of concept:

```text
HTTP POST -> Chatterbox Turbo on CPU -> WAV response
```

For the full model download and LocalLlmStack integration procedure, follow
[`instructions.md`](instructions.md).

## Layout

```text
chatterbox_api/
├── __main__.py  Starts Uvicorn, the HTTP server.
├── config.py    Reads the model path, host, and port from environment variables.
├── api.py       Defines the HTTP endpoints and loads the model at startup.
├── engine.py    Loads Chatterbox Turbo and generates speech.
└── audio.py     Converts Chatterbox's waveform tensor into an in-memory WAV file.
```

`__init__.py` only marks the directory as a Python package.

## What the demo intentionally does not include

- MP3 output
- selectable or cloned voices
- long-text splitting and audio joining
- request queues or concurrency protection
- authentication inside the TTS service
- custom error responses
- model or voice discovery endpoints
- automatic model downloads at runtime

The request model contains only `input`. Extra JSON properties sent by an
OpenAI-style client are ignored by Pydantic, and the response is always WAV.
The model snapshot's bundled `conds.pt` file supplies the single built-in voice.

## Standalone smoke test

After completing the download steps in `instructions.md`, run this from the
current directory.

### PowerShell

```powershell
$env:MODEL_DIR = "D:/Models"
docker compose -f compose.demo.yaml up --build
```

### Bash

```bash
export MODEL_DIR=/path/to/Models
docker compose -f compose.demo.yaml up --build
```

Generate speech:

```bash
curl --fail-with-body \
  --request POST \
  --header "Content-Type: application/json" \
  --data '{"input":"Hello from Chatterbox Turbo running on the CPU."}' \
  --output speech.wav \
  http://127.0.0.1:8105/v1/audio/speech
```

Open `speech.wav` in a media player to confirm the isolated service works before
connecting it to the rest of the stack.
