"""Chatbot-specific conversation scorers: sentiment per turn + trend across session."""
from __future__ import annotations

import numpy as np

from evaluator.models import get_sentiment


SENTIMENT_VALUE = {
    "positive": 1.0,
    "neutral": 0.0,
    "negative": -1.0,
    # variants some models emit:
    "pos": 1.0,
    "neg": -1.0,
    "neu": 0.0,
    "label_2": 1.0,   # cardiffnlp order: 0=neg, 1=neu, 2=pos
    "label_1": 0.0,
    "label_0": -1.0,
}


def _sentiment_score(text: str) -> float:
    """Return a scalar sentiment in [-1, 1], weighted by model confidence."""
    if not text.strip():
        return 0.0
    clf = get_sentiment()
    preds = clf(text[:512])
    if isinstance(preds, list) and preds and isinstance(preds[0], list):
        preds = preds[0]
    total = 0.0
    weight = 0.0
    for p in preds:
        label = p["label"].lower()
        val = SENTIMENT_VALUE.get(label)
        if val is None:
            continue
        total += val * float(p["score"])
        weight += float(p["score"])
    return total / weight if weight else 0.0


def _coerce_content(content) -> str:
    """Normalize a message content field to plain text.

    Handles plain strings and Gradio-6 multi-block content
    (list of {"type": "text", "text": "..."} dicts).
    """
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(str(block.get("text", "")))
            else:
                parts.append(str(block))
        return " ".join(parts).strip()
    return "" if content is None else str(content).strip()


def _extract_user_messages(history: list[dict]) -> list[str]:
    out = []
    for m in history:
        if m.get("role") != "user":
            continue
        text = _coerce_content(m.get("content"))
        if text:
            out.append(text)
    return out


def score_conversation(
    query: str,
    history: list[dict] | None,
) -> dict[str, float]:
    result: dict[str, float] = {}

    prior = _extract_user_messages(history or [])
    all_user_msgs = prior + ([query.strip()] if query and query.strip() else [])
    if not all_user_msgs:
        return result

    sentiments = [_sentiment_score(m) for m in all_user_msgs]
    result["user_sentiment_last"] = float(sentiments[-1])
    result["user_sentiment_mean"] = float(np.mean(sentiments))
    if len(sentiments) >= 2:
        result["sentiment_trend"] = float(sentiments[-1] - sentiments[0])

    return result
