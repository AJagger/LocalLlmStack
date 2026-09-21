#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import snapshot_download


NANO_REPOSITORY = "ResembleAI/chatterbox-nano"
NANO_REVISION = "71ccd1d0081b430592cea481f4307e764e07bc64"
REQUIRED_FILES = (
    "added_tokens.json",
    "conds.pt",
    "merges.txt",
    "s3gen_meanflow.safetensors",
    "special_tokens_map.json",
    "t3_nano_v1.safetensors",
    "tokenizer_config.json",
    "ve.safetensors",
    "vocab.json",
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download the pinned Chatterbox Nano runtime files for offline use."
    )
    parser.add_argument(
        "output",
        type=Path,
        help="Destination directory, e.g. /models/audio/tts/chatterbox-nano",
    )
    parser.add_argument("--revision", default=NANO_REVISION)
    args = parser.parse_args()

    destination = args.output.expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)

    snapshot_download(
        repo_id=NANO_REPOSITORY,
        revision=args.revision,
        local_dir=destination,
        allow_patterns=list(REQUIRED_FILES),
    )

    missing = [name for name in REQUIRED_FILES if not (destination / name).is_file()]
    if missing:
        raise SystemExit(f"download completed but files are missing: {', '.join(missing)}")

    print(f"Downloaded {NANO_REPOSITORY}@{args.revision} to {destination}")


if __name__ == "__main__":
    main()
