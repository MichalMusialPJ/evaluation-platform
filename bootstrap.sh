#!/usr/bin/env bash
# Idempotent bootstrap for the evaluation platform.
# Starts the full stack via docker compose: Langfuse, Ollama, evaluator.
# Safe to re-run.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log() { printf '\033[1;34m[bootstrap]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[bootstrap]\033[0m %s\n' "$*" >&2; exit 1; }

# 1. Check host dependencies
log "Checking host dependencies..."
command -v docker >/dev/null 2>&1 || die "docker not found. Install Docker Desktop: https://docs.docker.com/get-docker/"
docker compose version >/dev/null 2>&1 || die "docker compose plugin missing. Update Docker Desktop."

# 2. .env
if [ ! -f ".env" ]; then
    log "Copying .env.example -> .env"
    cp .env.example .env
else
    log ".env already exists (not overwriting)"
fi

# 3. Build + start all services
log "Building and starting all services (Langfuse, Ollama, evaluator)..."
docker compose up --build -d

# 4. Wait for Langfuse
log "Waiting for Langfuse to be healthy..."
LANGFUSE_HOST=$(grep -E '^LANGFUSE_HOST=' .env | cut -d '=' -f2- | tr -d '"' || true)
LANGFUSE_HOST="${LANGFUSE_HOST:-http://localhost:3000}"
URL="${LANGFUSE_HOST}/api/public/health"
for i in $(seq 1 60); do
    if curl -sf "$URL" >/dev/null 2>&1; then
        log "Langfuse healthy after ${i} attempt(s)"
        break
    fi
    [ "$i" -eq 60 ] && die "Langfuse did not become healthy at $URL"
    sleep 2
done

# Done
log "Bootstrap complete."
log "Langfuse UI: http://localhost:3000  (login: admin@local.dev / adminpass)"
log "Evaluator logs: docker compose logs -f evaluator"
log "Ollama model pull happens automatically on first evaluator start."
