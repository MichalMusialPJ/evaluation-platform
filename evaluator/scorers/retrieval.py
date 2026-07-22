"""Retrieval-side scorers: reranker over (query, chunks)."""
from __future__ import annotations

import numpy as np

from evaluator.models import get_reranker


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _chunk_text(chunk: dict) -> str:
    # New KB schema: {topic, text}. Keep small back-compat with old {question, answer}.
    topic = chunk.get("topic", "")
    text = chunk.get("text") or chunk.get("answer") or ""
    if topic:
        return f"{topic}: {text}".strip()
    q = chunk.get("question", "")
    return f"{q} {text}".strip()


def score_retrieval(query: str, contexts: list[dict]) -> dict[str, float]:
    if not query or not contexts:
        return {}

    reranker = get_reranker()
    pairs = [(query, _chunk_text(c)) for c in contexts]
    raw = np.asarray(reranker.predict(pairs), dtype=np.float32)
    norm = _sigmoid(raw)

    return {
        "context_relevance_mean": float(norm.mean()),
        "context_relevance_top1": float(norm.max()),
        "retrieval_margin": float(norm.max() - norm.mean()),
    }
