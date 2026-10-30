# Open WebUI Terminals setup

This change adds Open WebUI's Terminals integration to the stack. It lets a model propose commands, run them in a workspace container, read the result, and revise code based on the output. It is intended for development checks such as syntax validation and unit tests.

## Changes made

- Added the `terminals` orchestrator service using `ghcr.io/open-webui/terminals:latest` and the Open Terminal workspace image.
- Added the `TERMINAL_SERVER_CONNECTIONS` configuration to the existing `openwebui` service. Its address is `http://terminals:3000` on the Compose network. The actual service in this project is named `openwebui` (without a hyphen).
- Connected Open WebUI to the dedicated `terminals-net` network and named that Docker network `localllm-terminals`, matching `TERMINALS_NETWORK`.
- Marked `terminals-net` as an internal Docker network. Workspaces do not have general internet, LAN, or model-network access by default.
- Added a persistent `terminals-data` volume and a required `TERMINALS_API_KEY` environment entry.
- Did not publish a host port for the orchestrator.

## Configure the shared key

From the `server` directory, generate a key:

```bash
openssl rand -hex 32
```

An initial random key is already populated as `TERMINALS_API_KEY` in `server/.env`; Compose supplies the same value to Open WebUI and the orchestrator. To rotate it, generate a new value with the command above and replace the existing value. Keep the real key out of source control and share it only with administrators who manage this stack. The project ignores `server/.env` for future Git adds; if that file is already tracked in your repository, remove it from tracking before committing the generated key.

## Deploy

Run from `server`:

```bash
docker compose config --quiet
docker compose pull terminals
docker pull ghcr.io/open-webui/open-terminal:latest
docker compose up -d
docker compose ps
```

`docker compose config --quiet` should succeed after `TERMINALS_API_KEY` and the other required variables are populated in `.env`. The separate `docker pull` is needed because the workspace image is selected through `TERMINALS_IMAGE`, rather than as a service in this Compose file.

For an offline deployment, pull both images on a connected machine, save them with `docker save`, transfer the archive, and load them with `docker load`. Repeat this when updating either image. For a workplace deployment, pin tested image versions or digests instead of relying on `latest`.

## Use it in Open WebUI

1. Sign in as an Open WebUI administrator and check **Admin Panel → Settings → Integrations** for the configured **Code Terminal** connection. The environment-managed connection is recreated when Open WebUI starts because this stack sets `ENABLE_PERSISTENT_CONFIG=false`.
2. Open a chat with a model whose full serving path supports tool calls. Start with `general`; if tool calls are not emitted correctly, try the optional `quick-chat` model or verify the LiteLLM and model-server tool-call configuration.
3. Enable **Code Terminal** for that chat if Open WebUI has not already enabled it.
4. Ask for a small script, request that it run the script, and have it report the command, exit status, and output before revising the code if needed.

Users access the terminal through Open WebUI; they do not install a separate harness. A working integration still depends on the model issuing valid tool calls and the serving stack passing tool calls and results through correctly.

## Network and workplace considerations

The workspaces are attached only to `localllm-terminals`; they are not attached to `internal-llm-stack` or `exposed`. The network is internal, so generated code cannot download packages or reach network devices and services by default. For repeatable offline tests, build a workspace image with the required runtimes and packages preinstalled. If tests need a lab service, grant only the specific route required after reviewing what a generated script can reach.

The Docker backend mounts `/var/run/docker.sock` into the orchestrator. Access to that socket can control the host Docker daemon, so protect the orchestrator and consider a restricted Docker socket proxy before workplace use. The orchestrated workspaces are separate containers, but they share the `localllm-terminals` bridge network; an internal network blocks outside egress but does not isolate one workspace from other containers on that same network. For mutually untrusted users, use stronger per-workspace network isolation or a separately isolated code runner. This Compose configuration does not set CPU, memory, process, or disk quotas for workspace containers; define and enforce those limits before broader shared use.

Check the current Open WebUI Terminals licensing and deployment terms before workplace rollout. Treat successful sandbox tests as evidence for iteration, not as authorization to run generated scripts against production systems.

## Troubleshooting

- If Compose reports that `TERMINALS_API_KEY` is unset, check `server/.env` and ensure it is not blank.
- If the connection is unavailable, check `docker compose ps`, the `terminals` logs, and that both services are attached to `localllm-terminals`.
- If the tool is listed but the model does not invoke it, confirm the selected model's serving path supports tool calls end to end. The Compose configuration alone cannot make a model or API gateway produce valid tool calls.
- If the command runs but package installation or service access fails, check the workspace network restrictions above.
