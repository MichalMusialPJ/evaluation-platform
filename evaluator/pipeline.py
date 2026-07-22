"""Orchestrates scorers over an extracted trace dict.

Returns (scores, comments) where:
- scores   = {metric_name: float}
- comments = {metric_name: str}   subset — only metrics that came with reasoning
"""
from __future__ import annotations

import os

from evaluator.scorers.conversation import score_conversation
from evaluator.scorers.generation import score_generation
from evaluator.scorers.retrieval import score_retrieval


def _llm_judge_enabled() -> bool:
    return os.getenv("ENABLE_LLM_JUDGE", "false").lower() in ("true", "1", "yes")


def score_trace(fields: dict) -> tuple[dict[str, float], dict[str, str]]:
    query = fields.get("query") or ""
    answer = fields.get("answer") or ""
    contexts = fields.get("contexts") or []
    history = fields.get("history") or []

    scores: dict[str, float] = {}
    comments: dict[str, str] = {}

    scores.update(score_retrieval(query, contexts))
    scores.update(score_generation(query, answer, contexts))
    scores.update(score_conversation(query, history))

    if _llm_judge_enabled():
        # Lazy import to avoid Ollama startup cost when judge is disabled.
        from evaluator.scorers.llm_judge import score_llm_judge

        judge_scores, judge_comments = score_llm_judge(query, answer)
        scores.update(judge_scores)
        comments.update(judge_comments)

    return scores, comments
