#!/bin/bash
set -e

echo "[entrypoint] waiting for Langfuse..."
python scripts/wait_for_langfuse.py

if [ "${ENABLE_LLM_JUDGE:-false}" = "true" ]; then
  MODEL="${JUDGE_MODEL:-llama3.2:3b}"
  OLLAMA="${OLLAMA_HOST:-http://ollama:11434}"
  echo "[entrypoint] pulling Ollama model '${MODEL}' from ${OLLAMA}..."
  curl -sf -X POST "${OLLAMA}/api/pull" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"${MODEL}\"}" \
    --max-time 600 \
    || echo "[entrypoint] warning: model pull failed, continuing anyway"
fi

exec python -m evaluator.main
