"""Block until Langfuse is up on LANGFUSE_HOST, or fail after N attempts.

Called from bootstrap.sh and `make langfuse-up` — no manual poking needed.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv


def main() -> int:
    load_dotenv(Path(__file__).parent.parent / ".env")
    host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
    url = f"{host.rstrip('/')}/api/public/health"

    max_attempts = 60
    for attempt in range(1, max_attempts + 1):
        try:
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200:
                print(f"[wait] Langfuse healthy after {attempt} attempt(s): {url}")
                return 0
            print(f"[wait] attempt {attempt}: {resp.status_code}")
        except requests.RequestException as e:
            print(f"[wait] attempt {attempt}: {e.__class__.__name__}")
        time.sleep(2)

    print(f"[wait] Langfuse did NOT become healthy at {url} after {max_attempts} attempts", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
