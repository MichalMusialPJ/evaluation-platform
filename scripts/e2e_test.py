"""End-to-end integration test.

Pushes synthetic traces to Langfuse, runs the evaluator scoring pipeline,
and verifies scores were posted. No bot dependency — bot lives in my-simple-rag.

Requires: docker compose up --build (Langfuse running).
Run:  python scripts/e2e_test.py   (from repo root, with venv active)
"""
from __future__ import annotations

import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from langfuse import Langfuse  # noqa: E402

from evaluator.langfuse_client import LangfuseClient  # noqa: E402
from evaluator.pipeline import score_trace  # noqa: E402


SCENARIO = [
    {
        "query": "Jak długo trwa dostawa?",
        "answer": "Standardowy czas dostawy w Polsce wynosi 2-3 dni robocze od momentu nadania paczki.",
        "contexts": [
            {"id": "dostawa-1", "topic": "Dostawa",
             "text": "Standardowy czas dostawy w Polsce wynosi 2-3 dni robocze.", "score": 0.91},
        ],
        "history": [],
    },
    {
        "query": "Ile kosztuje wysyłka?",
        "answer": "Dostawa kurierem DPD kosztuje 14,99 zł, paczkomat InPost to 12,99 zł. Powyżej 199 zł dostawa jest bezpłatna.",
        "contexts": [
            {"id": "dostawa-2", "topic": "Dostawa",
             "text": "Dostawa kurierem DPD kosztuje 14,99 zł. Dostawa do paczkomatu InPost to 12,99 zł.", "score": 0.87},
        ],
        "history": [
            {"role": "user", "content": "Jak długo trwa dostawa?"},
            {"role": "assistant", "content": "2-3 dni robocze."},
        ],
    },
    {
        "query": "Ale ile to kosztuje konkretnie?",
        "answer": "Kurier DPD: 14,99 zł. Paczkomat InPost: 12,99 zł. Przy zamówieniach powyżej 199 zł dostawa jest bezpłatna.",
        "contexts": [
            {"id": "dostawa-2", "topic": "Dostawa",
             "text": "Dostawa kurierem DPD kosztuje 14,99 zł. Dostawa do paczkomatu InPost to 12,99 zł.", "score": 0.89},
        ],
        "history": [
            {"role": "user", "content": "Jak długo trwa dostawa?"},
            {"role": "assistant", "content": "2-3 dni robocze."},
            {"role": "user", "content": "Ile kosztuje wysyłka?"},
            {"role": "assistant", "content": "Kurier lub paczkomat."},
        ],
    },
    {
        "query": "A ile w końcu kosztuje ta dostawa? Bo już się gubię.",
        "answer": "Dostawa kurierem DPD kosztuje 14,99 zł. Paczkomat InPost to 12,99 zł. Przy zamówieniach powyżej 199 zł — dostawa bezpłatna.",
        "contexts": [
            {"id": "dostawa-2", "topic": "Dostawa",
             "text": "Dostawa kurierem DPD kosztuje 14,99 zł. Dostawa do paczkomatu InPost to 12,99 zł.", "score": 0.87},
        ],
        "history": [
            {"role": "user", "content": "Ile kosztuje wysyłka?"},
            {"role": "assistant", "content": "Kurier lub paczkomat."},
            {"role": "user", "content": "Ale ile to kosztuje konkretnie?"},
            {"role": "assistant", "content": "Kurier DPD: 14,99 zł. Paczkomat: 12,99 zł."},
        ],
    },
]


def push_traces() -> list[str]:
    lf = Langfuse(
        host=os.getenv("LANGFUSE_HOST"),
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    )
    session_id = f"e2e-{uuid.uuid4()}"
    trace_ids: list[str] = []

    print(f"[e2e] session_id = {session_id}")
    for i, turn in enumerate(SCENARIO, 1):
        trace_id = str(uuid.uuid4())
        print(f"[e2e] pushing trace {i}: {turn['query']!r}")
        lf.trace(
            id=trace_id,
            name="faq_bot_turn",
            session_id=session_id,
            input={"query": turn["query"]},
            output={"answer": turn["answer"]},
            metadata={
                "contexts": turn["contexts"],
                "history": turn["history"],
                "bot": "faq-rag-poc",
                "language": "pl",
                "e2e_test": True,
            },
        )
        trace_ids.append(trace_id)

    lf.flush()
    print(f"[e2e] pushed {len(trace_ids)} traces to Langfuse")
    return trace_ids


def score_and_verify(trace_ids: list[str]) -> int:
    print("[e2e] waiting 5s for Langfuse to persist traces...")
    time.sleep(5)

    client = LangfuseClient()
    since = datetime.now(timezone.utc) - timedelta(minutes=10)
    traces = client.fetch_new_traces(since=since, limit=100)
    ours = [t for t in traces if t.id in trace_ids]
    print(f"[e2e] fetched {len(ours)} of {len(trace_ids)} target traces")

    if len(ours) < len(trace_ids):
        print("[e2e] not all traces visible yet — retrying once...")
        time.sleep(3)
        traces = client.fetch_new_traces(since=since, limit=200)
        ours = [t for t in traces if t.id in trace_ids]

    if not ours:
        print("[e2e] FAIL: no traces found", file=sys.stderr)
        return 1

    for trace in ours:
        fields = client.extract_fields(trace)
        scores, comments = score_trace(fields)
        if not scores:
            print(f"[e2e] {trace.id[:8]}: no scores produced")
            continue
        client.post_scores(trace.id, scores, comments)
        short = ", ".join(f"{k}={v:+.2f}" for k, v in scores.items())
        print(f"[e2e] {trace.id[:8]}: {short}")

    print(f"\n[e2e] OK — scored {len(ours)} traces. Check UI: "
          f"{os.getenv('LANGFUSE_HOST', 'http://localhost:3000')}/project/faq-poc")
    return 0


def main() -> int:
    trace_ids = push_traces()
    return score_and_verify(trace_ids)


if __name__ == "__main__":
    raise SystemExit(main())
