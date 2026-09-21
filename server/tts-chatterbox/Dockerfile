# syntax=docker/dockerfile:1.7

FROM python:3.11-slim-bookworm AS wheel-builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
       build-essential \
       libsndfile1-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-runtime.txt ./

# Resolve the whole runtime dependency set in one pass so any package that
# depends on PyTorch is constrained to the CPU-only 2.6.0 wheels. Chatterbox
# itself is installed without dependencies so this headless service can omit
# its Gradio UI and multilingual-only packages.
RUN python -m pip install --upgrade "pip<26" "setuptools<81" wheel \
    && python -m pip wheel \
       --wheel-dir /wheels \
       --index-url https://download.pytorch.org/whl/cpu \
       --extra-index-url https://pypi.org/simple \
       --requirement requirements-runtime.txt \
    && python -m pip wheel \
       --wheel-dir /wheels \
       --no-deps \
       "s3tokenizer==0.3.0" \
       "chatterbox-tts==0.1.7"


FROM python:3.11-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    TOKENIZERS_PARALLELISM=false

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
       ffmpeg \
       libgomp1 \
       libsndfile1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 chatterbox \
    && useradd --system --uid 10001 --gid chatterbox --home-dir /app chatterbox

WORKDIR /app

COPY --from=wheel-builder /wheels /wheels
COPY requirements-runtime.txt ./

RUN python -m pip install --no-index --find-links=/wheels \
       --requirement requirements-runtime.txt \
    && python -m pip install --no-index --find-links=/wheels \
       --no-deps "s3tokenizer==0.3.0" "chatterbox-tts==0.1.7" \
    && rm -rf /wheels

# Fail the image build early if the trimmed dependency set cannot import the
# English Chatterbox path or if Perth's packaged CPU watermarker is incomplete.
RUN python - <<'PY'
import perth
import torch
import s3tokenizer.model_v2
from chatterbox.tts_turbo import ChatterboxTurboTTS

assert not torch.cuda.is_available()
assert ChatterboxTurboTTS is not None
assert perth.PerthImplicitWatermarker is not None
perth.PerthImplicitWatermarker()
PY

COPY --chown=chatterbox:chatterbox app ./app
COPY --chown=chatterbox:chatterbox voices/voices.yaml.example /voices/voices.yaml.example

USER chatterbox

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=600s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=4)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
