"""Generation-side scorers: NLI faithfulness + reranker answer relevance."""
from __future__ import annotations

import re

import numpy as np

from evaluator.models import get_nli, get_reranker


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + float(np.exp(-x)))


def _split_sentences(text: str) -> list[str]:
    # Simple PL/EN sentence splitter — good enough for POC.
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _chunk_text(chunk: dict) -> str:
    topic = chunk.get("topic", "")
    text = chunk.get("text") or chunk.get("answer") or ""
    if topic:
        return f"{topic}: {text}".strip()
    q = chunk.get("question", "")
    return f"{q} {text}".strip()


def score_generation(
    query: str,
    answer: str,
    contexts: list[dict],
) -> dict[str, float]:
    result: dict[str, float] = {}
    if not answer:
        return result

    # --- answer_relevance: reranker(query, answer)
    if query:
        reranker = get_reranker()
        raw = reranker.predict([(query, answer)])[0]
        result["answer_relevance"] = _sigmoid(float(raw))

    # --- faithfulness: fraction of answer sentences entailed by context
    if contexts:
        nli = get_nli()
        premise = "\n".join(_chunk_text(c) for c in contexts)
        sentences = _split_sentences(answer)
        if sentences:
            entail_probs = [
                nli.entailment_prob(premise, s) for s in sentences
            ]
            # Two variants: soft mean + hard fraction over 0.5.
            result["faithfulness"] = float(np.mean(entail_probs))
            result["faithfulness_hard"] = float(
                np.mean([p > 0.5 for p in entail_probs])
            )

    return result
