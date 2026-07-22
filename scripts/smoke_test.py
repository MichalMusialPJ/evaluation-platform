"""Offline sanity: run the full scoring pipeline on a fixture trace, print scores.

Does NOT require Langfuse or Ollama to be running. Requires:
- Python deps installed
- Model files downloadable from HF (first run: ~500 MB)

Run:  python scripts/smoke_test.py   (from Code/)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

FIXTURE = ROOT / "tests" / "fixtures" / "sample_trace.json"


def main() -> int:
    from evaluator.pipeline import score_trace

    if not FIXTURE.exists():
        print(f"[smoke] fixture missing: {FIXTURE}", file=sys.stderr)
        return 1

    trace = json.loads(FIXTURE.read_text(encoding="utf-8"))
    print(f"[smoke] scoring fixture: {FIXTURE.name}")
    print(f"[smoke] query:  {trace['query']!r}")
    print(f"[smoke] answer: {trace['answer']!r}")
    print(f"[smoke] {len(trace.get('contexts', []))} context chunk(s), "
          f"{len(trace.get('history', []))} history msg(s)")

    scores, comments = score_trace(trace)
    print("\n[smoke] scores:")
    for k, v in sorted(scores.items()):
        line = f"  {k:30s} = {v:+.4f}"
        if k in comments:
            line += f"   # {comments[k]}"
        print(line)

    if not scores:
        print("[smoke] ERROR: no scores produced", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
