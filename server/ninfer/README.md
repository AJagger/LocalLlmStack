# LocalLLMStack NInfer image

We use a version of NInfer with `curl` added, so that we can reuse the main stack's health-check logic.

This directory stores the LocalLLMStack Dockerfile for this version of NInfer, 
which is the complete NInfer Dockerfile from https://github.com/Neroued/ninfer/ (commit `da49c0d60f477626a608b22e735957ef3425ee9b`), 
but with `curl` installed in the final runtime stage.

## Build instructions

From a directory alongside the LocalLLMStack checkout:

```bash
git clone https://github.com/Neroued/ninfer.git
git -C ninfer checkout da49c0d60f477626a608b22e735957ef3425ee9b

./LocalLlmStack/server/ninfer/build-image.sh \
  ./ninfer \
  local/ninfer:da49c0d-local1
```

## Moving the image to an offline host

On the build machine:

```bash
docker image save \
  --output ninfer-da49c0d-local1.tar \
  local/ninfer:da49c0d-local1
```

On the offline deployment host:

```bash
docker image load --input ninfer-da49c0d-local1.tar
docker image inspect local/ninfer:da49c0d-local1
```
