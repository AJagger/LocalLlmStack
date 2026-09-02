#!/usr/bin/env bash
set -euo pipefail

readonly EXPECTED_NINFER_COMMIT="da49c0d60f477626a608b22e735957ef3425ee9b"
readonly DEFAULT_IMAGE="local/ninfer:da49c0d-local1"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<USAGE
Usage: $(basename "$0") PATH_TO_NINFER_SOURCE [IMAGE_NAME]

Build the LocalLLMStack NInfer image from the pinned NInfer source revision.

Arguments:
  PATH_TO_NINFER_SOURCE  Checkout or extracted source tree for Neroued/ninfer.
  IMAGE_NAME             Optional image name and tag.
                         Default: ${DEFAULT_IMAGE}

Example:
  $(basename "$0") ../../ninfer ${DEFAULT_IMAGE}
USAGE
}

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage >&2
  exit 2
fi

source_dir="$(cd "$1" && pwd)"
image_name="${2:-$DEFAULT_IMAGE}"

for command_name in docker git; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Error: required command not found: $command_name" >&2
    exit 1
  fi
done

if [[ ! -f "$source_dir/CMakeLists.txt" ]]; then
  echo "Error: $source_dir does not look like the NInfer source tree." >&2
  exit 1
fi

actual_commit="$(git -C "$source_dir" rev-parse HEAD)"
if [[ "$actual_commit" != "$EXPECTED_NINFER_COMMIT" ]]; then
  cat >&2 <<ERROR
Error: unexpected NInfer source revision.
Expected: $EXPECTED_NINFER_COMMIT
Actual:   $actual_commit

Check out the expected revision before building:
  git -C "$source_dir" checkout $EXPECTED_NINFER_COMMIT
ERROR
  exit 1
fi

echo "Building image: $image_name"
echo "NInfer source: $source_dir"
echo "NInfer commit: $actual_commit"

docker build \
  --file "$SCRIPT_DIR/Dockerfile" \
  --tag "$image_name" \
  --label "org.opencontainers.image.source=https://github.com/Neroued/ninfer" \
  --label "org.opencontainers.image.revision=$actual_commit" \
  --label "local.llm.variant=curl-healthcheck" \
  "$source_dir"

echo
echo "Built successfully: $image_name"
docker image inspect \
  --format 'Image ID: {{.Id}}\nCreated: {{.Created}}\nSize: {{.Size}} bytes' \
  "$image_name"
