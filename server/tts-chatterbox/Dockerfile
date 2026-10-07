FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

WORKDIR /app

# git is required by one of Chatterbox's Python dependencies.
# libsndfile1 is used by Chatterbox's audio stack.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch first. The later Chatterbox installation reuses it
# rather than pulling a CUDA-enabled PyTorch build.
RUN python -m pip install \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.6.0 \
    torchaudio==2.6.0

COPY requirements.txt .
RUN python -m pip install -r requirements.txt

COPY chatterbox_api ./chatterbox_api

EXPOSE 8000

CMD ["python", "-m", "chatterbox_api"]
