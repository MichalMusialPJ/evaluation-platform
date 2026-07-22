"""Evaluator polling loop.

Pulls new traces from Langfuse, runs scorers, posts scores back.
Run:  python -m evaluator.main   (from Code/)
"""
from __future__ import annotations

import time
import traceback
from datetime import datetime, timedelta, timezone

from evaluator.config import POLL_INTERVAL_SEC
from evaluator.langfuse_client import LangfuseClient
from evaluator.pipeline import score_trace


def main() -> None:
    client = LangfuseClient()
    # Look back a bit further on the very first fetch to catch traces
    # created shortly before evaluator started.
    since = datetime.now(timezone.utc) - timedelta(minutes=15)

    print(f"[evaluator] polling every {POLL_INTERVAL_SEC}s (initial lookback 15 min)")

    while True:
        try:
            traces = client.fetch_new_traces(since=since)
            if traces:
                print(f"[evaluator] found {len(traces)} new trace(s)")
            for trace in traces:
                fields = client.extract_fields(trace)
                if not fields.get("query") or not fields.get("answer"):
                    print(f"[evaluator] skip {trace.id}: missing query/answer")
                    client.mark_processed(trace.id)
                    continue
                scores, comments = score_trace(fields)
                if not scores:
                    print(f"[evaluator] skip {trace.id}: no scores produced")
                    client.mark_processed(trace.id)
                    continue
                client.post_scores(trace.id, scores, comments)
                client.mark_processed(trace.id)
                short = ", ".join(f"{k}={v:.2f}" for k, v in scores.items())
                print(f"[evaluator] scored {trace.id}: {short}")
        except KeyboardInterrupt:
            print("\n[evaluator] interrupted")
            break
        except Exception:
            print("[evaluator] error in loop:")
            traceback.print_exc()

        # Advance the window; keep small overlap to avoid missing edge cases.
        since = datetime.now(timezone.utc) - timedelta(seconds=POLL_INTERVAL_SEC * 3)
        time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    main()
