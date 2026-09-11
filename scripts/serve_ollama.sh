#!/usr/bin/env bash
# Run the manually installed local runtime from the repository root.
set -eu
project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
export OLLAMA_HOST=127.0.0.1:11434
export OLLAMA_MODELS="$project_root/data/models/ollama"
export OLLAMA_NO_CLOUD=1
export OLLAMA_NUM_PARALLEL=1
exec "$project_root/data/runtime/ollama/bin/ollama" serve
