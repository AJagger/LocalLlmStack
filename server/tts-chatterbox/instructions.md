# Integrating Chatterbox Turbo into LocalLlmStack

These instructions start with the supplied ZIP and end with Chatterbox Turbo
available through:

```text
Open WebUI
    -> external-gateway-proxy
    -> LiteLLM model alias: speech
    -> internal-model-router:8105
    -> chatterbox-tts container
```

The implementation remains deliberately minimal:

- CPU inference only
- one built-in voice from `conds.pt`
- WAV output only
- one request body field used by the application: `input`
- no request queue or concurrency protection
- no text splitting inside the TTS service

Open WebUI and LiteLLM send additional OpenAI-compatible fields such as
`model`, `voice`, and `response_format`. Pydantic ignores those extra fields in
this demo, so they do not prevent the request from working.

## 1. Prerequisites

You need:

- the current `LocalLlmStack` repository
- Docker with the Compose plugin
- Python available on the machine used to download the model
- enough disk space for the Chatterbox Turbo snapshot and Docker image
- enough system RAM to load the 350M-parameter Turbo model on CPU

Run all repository commands from the `server` directory unless a step says
otherwise.

## 2. Extract the ZIP into the repository

The ZIP already contains the path:

```text
server/audio/tts-chatterbox/
```

Extract it into the root of `LocalLlmStack`, not into the existing `server`
directory. The result should be:

```text
LocalLlmStack/
├── client/
└── server/
    ├── compose.yaml
    ├── internal-model-router.nginx.conf.template
    ├── internal-model-gateway.litellm.config.yaml
    └── audio/
        └── tts-chatterbox/
            ├── Dockerfile
            ├── instructions.md
            ├── requirements.txt
            └── chatterbox_api/
```

If extracting manually, copying the `tts-chatterbox` directory to
`LocalLlmStack/server/audio/tts-chatterbox` produces the same result.

## 3. Download Chatterbox Turbo

The runtime container is configured for offline model loading. Download the
model before starting Docker.

### Install the Hugging Face CLI

PowerShell:

```powershell
python -m pip install -U huggingface_hub
hf --help
```

Bash:

```bash
python -m pip install -U huggingface_hub
hf --help
```

The model is public, so a Hugging Face login is normally unnecessary.

### Download to the LocalLlmStack model directory

Use the same host directory already assigned to `MODEL_DIR` in `server/.env`.
For example, if `.env` contains:

```dotenv
MODEL_DIR=D:/Models
```

run in PowerShell:

```powershell
$env:MODEL_DIR = "D:/Models"

hf download ResembleAI/chatterbox-turbo `
  --local-dir "$env:MODEL_DIR/audio/tts/chatterbox-turbo"
```

Linux/macOS example:

```bash
export MODEL_DIR=/path/to/Models

hf download ResembleAI/chatterbox-turbo \
  --local-dir "$MODEL_DIR/audio/tts/chatterbox-turbo"
```

The resulting layout should include:

```text
$MODEL_DIR/
└── audio/
    └── tts/
        └── chatterbox-turbo/
            ├── t3_turbo_v1.safetensors
            ├── s3gen_meanflow.safetensors
            ├── ve.safetensors
            ├── conds.pt
            ├── tokenizer_config.json
            ├── vocab.json
            └── merges.txt
```

Do not download the Nano repository for this version. Turbo's local loader
expects `t3_turbo_v1.safetensors`; Nano contains the differently sized
`t3_nano_v1.safetensors` checkpoint.

## 4. Test the isolated container first

This step is optional but strongly recommended because it separates Chatterbox
or CPU problems from gateway configuration problems.

From `server/audio/tts-chatterbox`:

PowerShell:

```powershell
$env:MODEL_DIR = "D:/Models"
docker compose -f compose.demo.yaml up --build
```

Bash:

```bash
export MODEL_DIR=/path/to/Models
docker compose -f compose.demo.yaml up --build
```

Wait until the container is healthy:

```bash
docker compose -f compose.demo.yaml ps
```

Then create a WAV file:

```bash
curl --fail-with-body \
  --request POST \
  --header "Content-Type: application/json" \
  --data '{"input":"Hello from Chatterbox Turbo running on the CPU."}' \
  --output speech.wav \
  http://127.0.0.1:8105/v1/audio/speech
```

PowerShell alternative:

```powershell
$body = @{
    input = "Hello from Chatterbox Turbo running on the CPU."
} | ConvertTo-Json

Invoke-WebRequest `
    -Uri "http://127.0.0.1:8105/v1/audio/speech" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body `
    -OutFile "speech.wav"
```

Stop the isolated demo before integrating it so that only one copy of the model
is consuming CPU and RAM while you test the stack:

```bash
docker compose -f compose.demo.yaml down
```

## 5. Add the TTS service to `server/compose.yaml`

Add this service beneath the existing model services and before the routing and
gateway section:

```yaml
  # CPU-only text-to-speech service.
  chatterbox-tts:
    build:
      context: ./audio/tts-chatterbox
    expose:
      - "8000"
    environment:
      CHATTERBOX_MODEL_PATH: /models/audio/tts/chatterbox-turbo
    volumes:
      - type: bind
        source: ${MODEL_DIR:?MODEL_DIR must be set in .env}
        target: /models
        read_only: true
    networks:
      - internal-llm-stack
    restart: unless-stopped
    logging: *json-logging
    healthcheck:
      test:
        - CMD
        - python
        - -c
        - import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=5)
      interval: 30s
      timeout: 5s
      retries: 5
      start_period: 300s
    profiles:
      - audio
```

Important details:

- There is no host `ports` entry. The service remains private to the internal
  Docker network.
- The full `MODEL_DIR` is mounted at `/models`, matching the rest of the stack.
- `CHATTERBOX_MODEL_PATH` therefore resolves to the files downloaded in step 3.
- The `audio` profile keeps TTS optional. Start the stack with `--profile audio`
  whenever speech is required.
- The service does not reserve an NVIDIA device and uses CPU-only PyTorch.

## 6. Add the speech route to the internal NGINX router

In the `internal-model-router` service in `server/compose.yaml`, add the backend
environment variable:

```yaml
    environment:
      GENERAL_MODEL: http://llamacpp-general:8000
      AUTOCOMPLETE_MODEL: http://llamacpp-autocomplete:8000
      QUICK_CHAT_MODEL: http://vllm-quick-chat:8000
      VISION_MODEL: http://vllm-vision:8000
      SPEECH_MODEL: http://chatterbox-tts:8000
```

Add port `8105` to its `expose` list:

```yaml
    expose:
      - "8080" # Local NGINX health listener.
      - "8101" # General model route.
      - "8102" # Autocomplete model route.
      - "8103" # Quick-chat model route.
      - "8104" # Vision model route.
      - "8105" # Text-to-speech route.
```

Do not add `chatterbox-tts` to the router's `depends_on`. Keeping that dependency
out allows the normal core stack to start without enabling the `audio` profile.
NGINX resolves the backend when an audio request is made.

Now add this block to
`server/internal-model-router.nginx.conf.template`, before the healthcheck
server:

```nginx
# Text to speech
server {
    listen 8105;

    client_max_body_size 2m;

    location / {
        set $backend ${SPEECH_MODEL};
        proxy_pass $backend$request_uri;

        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Authorization $http_authorization;

        proxy_buffering off;
        proxy_request_buffering off;
        proxy_cache off;

        proxy_connect_timeout 30s;
        proxy_send_timeout 1800s;
        proxy_read_timeout 1800s;
    }
}
```

This creates a stable internal speech role at:

```text
http://internal-model-router:8105
```

## 7. Add the `speech` model alias to LiteLLM

Append this item to `model_list` in
`server/internal-model-gateway.litellm.config.yaml`:

```yaml
  - model_name: speech
    litellm_params:
      model: openai/tts-1
      api_base: http://internal-model-router:8105/v1
      api_key: sk-internal
```

Use `openai/tts-1` as the internal LiteLLM provider model even though the real
model is Chatterbox Turbo. This makes LiteLLM use its supported OpenAI TTS code
path. The public model alias remains `speech`, and the minimal backend ignores
the forwarded provider model name.

After this change, authenticated clients can use:

```text
POST /v1/audio/speech
model: speech
```

through the same external gateway already used for chat models.

## 8. Configure Open WebUI

In the `openwebui` service's `environment` section in `server/compose.yaml`, add:

```yaml
      AUDIO_TTS_ENGINE: openai
      AUDIO_TTS_OPENAI_API_BASE_URL: http://external-gateway-proxy:8000/v1
      AUDIO_TTS_OPENAI_API_KEY: ${LITELLM_MASTER_KEY:?LITELLM_MASTER_KEY must be set}
      AUDIO_TTS_MODEL: speech
      AUDIO_TTS_VOICE: alloy
      AUDIO_TTS_OPENAI_PARAMS: '{"response_format":"wav"}'
      AUDIO_TTS_SPLIT_ON: "none"
```

Why these values are used:

- `openai` selects Open WebUI's OpenAI-compatible TTS client.
- The API base URL uses the existing authenticated gateway.
- `speech` is the stable LiteLLM alias added in step 7.
- `alloy` is only a compatibility value in this minimal implementation; the
  service always uses the one bundled `conds.pt` voice.
- The service always returns WAV, so the requested response format is set to
  `wav` for clarity.
- `none` sends one request for the complete response. The minimal TTS service
  does not join multiple generated clips, and your stated priority is avoiding
  stop-start playback.

Do not add `speech` to `OPENAI_API_CONFIGS.model_ids`. That list controls the
normal chat-model selector, while `speech` is an audio service role rather than
a chat-completion model.

Because the stack currently sets `ENABLE_PERSISTENT_CONFIG=false`, the Compose
environment values remain authoritative after Open WebUI restarts.

## 9. Build and start the integrated stack

From `LocalLlmStack/server`:

```bash
docker compose --profile audio up -d --build
```

To include the existing optional models as well:

```bash
docker compose --profile audio --profile extended-models up -d --build
```

Check status:

```bash
docker compose --profile audio ps
```

Follow the TTS logs during its first startup:

```bash
docker compose --profile audio logs -f chatterbox-tts
```

Turbo is larger than Nano and CPU startup or generation may take noticeably
longer. The healthcheck allows five minutes for initial loading.

## 10. Verify the complete gateway path

### Bash

From `server`, where `.env` contains `LITELLM_MASTER_KEY`:

```bash
set -a
. ./.env
set +a

curl --fail-with-body \
  http://127.0.0.1:${LLM_GATEWAY_PORT:-8000}/v1/audio/speech \
  --header "Authorization: Bearer $LITELLM_MASTER_KEY" \
  --header "Content-Type: application/json" \
  --data '{
    "model": "speech",
    "input": "The integrated Chatterbox Turbo endpoint is working.",
    "voice": "alloy",
    "response_format": "wav"
  }' \
  --output speech.wav
```

### PowerShell

PowerShell does not automatically import Compose `.env` values into the current
shell. Assign the same key used in `server/.env`:

```powershell
$gatewayPort = 8000
$liteLlmKey = "replace-with-the-LITELLM_MASTER_KEY-from-server-.env"

$body = @{
    model = "speech"
    input = "The integrated Chatterbox Turbo endpoint is working."
    voice = "alloy"
    response_format = "wav"
} | ConvertTo-Json

Invoke-WebRequest `
    -Uri "http://127.0.0.1:$gatewayPort/v1/audio/speech" `
    -Headers @{ Authorization = "Bearer $liteLlmKey" } `
    -Method Post `
    -ContentType "application/json" `
    -Body $body `
    -OutFile "speech.wav"
```

Open `speech.wav`. A successful result proves this complete path:

```text
host -> external proxy -> LiteLLM -> internal router -> Chatterbox Turbo
```

## 11. Test from Open WebUI

1. Open the existing Open WebUI address, normally `http://127.0.0.1:3000`.
2. Start or open a chat.
3. Generate an assistant response.
4. Click the speaker/read-aloud icon on the assistant message.
5. Wait for the CPU generation to finish; the browser should then play the WAV.

The model accepts native paralinguistic tags such as `[laugh]`, `[chuckle]`, and
`[cough]`. They can be tested by sending them in the text, although ordinary LLM
responses will not normally contain them without prompting.

## 12. Starting and stopping later

Start the core stack with TTS:

```bash
docker compose --profile audio up -d
```

Start TTS plus the existing extended models:

```bash
docker compose --profile audio --profile extended-models up -d
```

Stop everything:

```bash
docker compose down
```

Rebuild only the TTS image after changing its Python files or Dockerfile:

```bash
docker compose --profile audio build chatterbox-tts
docker compose --profile audio up -d chatterbox-tts
```

Model files are bind-mounted and are not baked into the image, so replacing the
model snapshot does not require rebuilding the image. Restart the container
after changing model files.

## 13. Troubleshooting

### `t3_turbo_v1.safetensors` not found

The Nano model was downloaded, the path is wrong, or `MODEL_DIR` differs between
`.env` and the download command. Confirm this exact host file exists:

```text
$MODEL_DIR/audio/tts/chatterbox-turbo/t3_turbo_v1.safetensors
```

### `Please prepare_conditionals first` or missing voice conditioning

Confirm this file exists:

```text
$MODEL_DIR/audio/tts/chatterbox-turbo/conds.pt
```

The minimal service relies on the bundled conditionals and does not accept a
reference voice file.

### The container stays unhealthy

Inspect logs:

```bash
docker compose --profile audio logs chatterbox-tts
```

Common causes are insufficient RAM, an incomplete download, or a wrong bind
mount. Also inspect the mounted directory from inside the container:

```bash
docker compose --profile audio run --rm chatterbox-tts \
  ls -lah /models/audio/tts/chatterbox-turbo
```

### Direct service works but the gateway request fails

Recreate the routing and gateway containers so they load the edited files:

```bash
docker compose --profile audio up -d --force-recreate \
  internal-model-router internal-model-gateway external-gateway-proxy openwebui
```

Then inspect:

```bash
docker compose logs internal-model-router internal-model-gateway
```

The repository currently pins LiteLLM. Audio proxy behaviour should be tested
with that exact version using the gateway curl command in step 10 before relying
on Open WebUI.

### Open WebUI still uses old audio settings

Recreate it after editing Compose:

```bash
docker compose --profile audio up -d --force-recreate openwebui
```

Also check the user's personal Audio settings because user-level selections can
override some server defaults.

### WAV is generated but playback is delayed

That is expected for this proof of concept. Turbo runs entirely on CPU, the
endpoint is non-streaming, and the whole WAV is returned only after generation
finishes.

## 14. Known limitations of this minimal integration

This is enough to demonstrate and use the capability, but it is not yet a
production-quality shared service:

- concurrent requests are not serialized
- there is no bounded queue
- long responses are not chunked inside the service
- there is only one voice
- the `voice`, `speed`, and `response_format` request values are ignored
- all output is WAV
- input length is not limited
- authentication is enforced by LiteLLM, not by the TTS container itself

The first hardening change should be serializing inference requests, because the
single model instance is shared by all HTTP requests. After that, add input
limits, a bounded queue, long-text chunking, and fixed voice presets as needed.

## 15. Official references

- Chatterbox source and Turbo usage: https://github.com/resemble-ai/chatterbox
- Chatterbox Turbo model files: https://huggingface.co/ResembleAI/chatterbox-turbo
- Hugging Face `hf download` documentation: https://huggingface.co/docs/huggingface_hub/guides/cli
- LiteLLM `/audio/speech` documentation: https://docs.litellm.ai/docs/text_to_speech
- Open WebUI OpenAI-compatible TTS configuration: https://docs.openwebui.com/features/chat-conversations/audio/text-to-speech/openai-tts-integration/
