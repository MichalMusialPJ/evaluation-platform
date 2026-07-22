"""Thin adapter around the Langfuse SDK — fetch traces, post scores."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from langfuse import Langfuse

from evaluator.config import (
    LANGFUSE_HOST,
    LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY,
)


class LangfuseClient:
    def __init__(self):
        self.lf = Langfuse(
            host=LANGFUSE_HOST,
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
        )
        self._processed: set[str] = set()

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------
    def fetch_new_traces(
        self,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list:
        """Return trace objects not yet processed in this run."""
        # Default: 1h back on first call — SDK requires *some* window in v2.
        since = since or (datetime.now(timezone.utc) - timedelta(hours=1))
        page = self.lf.api.trace.list(
            limit=limit,
            from_timestamp=since,
            order_by="timestamp.asc",
        )
        return [t for t in page.data if t.id not in self._processed]

    # ------------------------------------------------------------------
    # Extract
    # ------------------------------------------------------------------
    @staticmethod
    def extract_fields(trace) -> dict:
        """Pull the fields our scorers need out of a Langfuse trace object.

        Bot writes:
          input    = {"query": ...}
          output   = {"answer": ...}
          metadata = {"contexts": [...], "history": [...]}
        """
        inp = trace.input or {}
        out = trace.output or {}
        meta = trace.metadata or {}

        return {
            "query": inp.get("query") if isinstance(inp, dict) else None,
            "answer": out.get("answer") if isinstance(out, dict) else None,
            "contexts": meta.get("contexts", []) if isinstance(meta, dict) else [],
            "history": meta.get("history", []) if isinstance(meta, dict) else [],
        }

    # ------------------------------------------------------------------
    # Post
    # ------------------------------------------------------------------
    def post_scores(
        self,
        trace_id: str,
        scores: dict,
        comments: dict | None = None,
    ) -> None:
        comments = comments or {}
        for name, value in scores.items():
            kwargs = {"trace_id": trace_id, "name": name, "value": float(value)}
            if name in comments and comments[name]:
                kwargs["comment"] = comments[name]
            self.lf.score(**kwargs)
        self.lf.flush()

    def mark_processed(self, trace_id: str) -> None:
        self._processed.add(trace_id)
