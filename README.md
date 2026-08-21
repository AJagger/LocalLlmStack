# LocalLLMStack

A fully local, offline LLM stack for local development. It serves several local models through a single OpenAI-compatible API, with a browser chat UI (Open WebUI) and IDE integration (Continue for VS Code) as consumers.

## Components

### Model servers

| Service | Engine | Model | Role | Notes |
|---|---|---|---|---|
| `llamacpp-general` | llama.cpp (CUDA) | Qwen3.8-27B (Q6_K GGUF) | `general` | Primary general-purpose model. 128K context, full GPU offload, flash attention, q8_0 KV cache, reasoning support. Starts first and claims the GPU. |
| `llamacpp-autocomplete` | llama.cpp (CUDA) | Qwen2.5-Coder-1.5B (Q8_0 GGUF) | `autocomplete` | Fill-in-the-middle model for IDE tab completion. 8K context, KV in system RAM, spills to CPU if needed (`FIT: on`). |
| `vllm-quick-chat` | vLLM | Qwen3.5-2B | `quick-chat` | *Optional* (`extended-models` profile). Small fast model for short interactions and tool use. |
| `vllm-vision` | vLLM | Qwen3-VL-8B-Instruct (FP8) | `vision` | *Optional* (`extended-models` profile). Vision model, up to 2 images per prompt. |



### Routing and gateway

| Service | Image | Purpose |
|---|---|---|
| `internal-model-router` | nginx | Maps constant role ports (8101–8104) to the current model containers. Backends are injected as environment variables (`GENERAL_MODEL`, `AUTOCOMPLETE_MODEL`, `QUICK_CHAT_MODEL`, `VISION_MODEL`) and rendered into the nginx config from a template. |
| `internal-model-gateway` | LiteLLM | Presents all model roles through one OpenAI-compatible API on port 4000. Requires `LITELLM_MASTER_KEY` for authentication. |
| `external-gateway-proxy` | nginx | The only container that can reach the internal stack from outside. Publishes the gateway to the host at `${LLM_GATEWAY_IP:-127.0.0.1}:${LLM_GATEWAY_PORT:-8000}`. |

### Consumers

| Consumer | How it connects |
|---|---|
| **Open WebUI** (Docker service) | Browser-based chat UI at `${OPENWEBUI_IP:-127.0.0.1}:${OPENWEBUI_PORT:-3000}`. Runs in offline mode, talks to the external proxy, and lists the `general`, `quick-chat`, and `vision` models. Data (users, conversations, settings) persists in the `open-webui-data` volume. |
| **Continue** (VS Code) | Client-side config in [`client/vscode/continue.config.yaml`](client/vscode/continue.config.yaml). Uses `general` for Chat/Agent/Edit/Apply (with tool use) and `autocomplete` for FIM tab completion via the legacy completions endpoint. |

## Prerequisites

- Docker with the Compose plugin
- NVIDIA GPU(s) with the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) installed
- Model weights downloaded locally into `MODEL_DIR` (see below)

### Model files

Models are loaded from the directory set in `MODEL_DIR` (bind-mounted read-only at `/models` in every model container). Expected layout:

```
$MODEL_DIR/
├── Qwen3.8-27B-GGUF/
│   └── Qwen3.8-27B-Q6_K.gguf
├── Qwen2.5-Coder-1.5B-Q8_0-GGUF/
│   └── qwen2.5-coder-1.5b-q8_0.gguf
├── Qwen3.5-2B/                  # (extended-models profile)
└── Qwen3-VL-8B-Instruct-FP8/    # (extended-models profile)
```

## Setup

### 1. Configure environment

Copy the environment template and fill in the required values in `server/.env`:

| Variable | Required | Default | Description |
|---|---|---|---|
| `MODEL_DIR` | yes | — | Host path to the directory containing model weights. |
| `LITELLM_MASTER_KEY` | yes | — | API key for the LiteLLM gateway. Used by Open WebUI and any external API clients. |
| `WEBUI_SECRET_KEY` | yes | — | Secret key for Open WebUI session signing. |
| `LLM_GATEWAY_IP` | no | `127.0.0.1` | Host interface the LLM API is published on. |
| `LLM_GATEWAY_PORT` | no | `8000` | Host port for the LLM API. |
| `OPENWEBUI_IP` | no | `127.0.0.1` | Host interface Open WebUI is published on. |
| `OPENWEBUI_PORT` | no | `3000` | Host port for Open WebUI. |


### 2. Start the stack

```bash
cd server

# Core stack (general + autocomplete models, router, gateway, proxy, Open WebUI)
docker compose up -d

# Include the optional quick-chat and vision models
docker compose --profile extended-models up -d
```

The `extended-models` aren't started by default.

### 3. Verify

```bash
docker compose ps          # all services should reach "healthy"
curl http://127.0.0.1:8000/health/readiness
```

First startup of the 27B general model can take around five minutes (its healthcheck allows up to 10 minutes).

## Usage

### Open WebUI

Open <http://127.0.0.1:3000> in a browser. The `general`, `quick-chat`, and `vision` models appear under the "Local" tag.

### OpenAI-compatible API

Any OpenAI client can point at the gateway:

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "general",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

Available model names: `general`, `autocomplete`, `quick-chat`, `vision`.

### Continue (VS Code)

1. Install the [Continue](https://continue.dev) extension.
2. Load the config from [`client/vscode/continue.config.yaml`](client/vscode/continue.config.yaml) (e.g. via *Continue → Settings → Import Config*).
3. Update the `apiKey` values to match your `LITELLM_MASTER_KEY`.

- **Chat / Agent / Edit / Apply** use the `general` model (128K context, tool use enabled).
- **Tab autocomplete** uses the `autocomplete` FIM model with tuned stop words and a 5 s timeout.

## Operations

```bash
cd server

docker compose ps                          # service status & health
docker compose logs -f llamacpp-general    # follow logs for one service
docker compose restart vllm-vision         # restart a single service
docker compose down                        # stop the stack (data volume is kept)
```

- **Swapping a model backend:** change the `*_MODEL` environment variables on `internal-model-router` (and the model path in the model service) — consumers keep working because they only know role names.
- **Open WebUI settings:** `ENABLE_PERSISTENT_CONFIG` is `false`, so environment configuration is authoritative; changes made in the Open WebUI admin UI are reset on restart.
- **Logs** are bounded (50 MB × 3 per service) and will not grow without limit.