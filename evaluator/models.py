"""Lazy-loaded singleton models. First call = download + load; subsequent = free."""
from __future__ import annotations

from functools import lru_cache

import torch
from sentence_transformers import CrossEncoder
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    pipeline,
)

from evaluator.config import (
    NLI_MODEL,
    RERANKER_MODEL,
    SENTIMENT_MODEL,
)


@lru_cache(maxsize=1)
def get_reranker() -> CrossEncoder:
    print(f"[models] loading reranker: {RERANKER_MODEL}")
    return CrossEncoder(RERANKER_MODEL)


@lru_cache(maxsize=1)
def get_sentiment():
    print(f"[models] loading sentiment: {SENTIMENT_MODEL}")
    return pipeline(
        "text-classification",
        model=SENTIMENT_MODEL,
        top_k=None,  # return all label scores
    )


class NLI:
    """Direct NLI wrapper (premise, hypothesis) → probs for entail/neutral/contradict."""

    def __init__(self, model_name: str):
        print(f"[models] loading NLI: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.eval()
        # Label order for XNLI-style DeBERTa is typically: entailment, neutral, contradiction.
        # Read it off the model config to be safe.
        id2label = self.model.config.id2label
        self.entail_idx = next(
            (i for i, lbl in id2label.items() if "entail" in lbl.lower()), 0
        )
        self.contradict_idx = next(
            (i for i, lbl in id2label.items() if "contradict" in lbl.lower()), 2
        )

    @torch.inference_mode()
    def entailment_prob(self, premise: str, hypothesis: str) -> float:
        inputs = self.tokenizer(
            premise, hypothesis, return_tensors="pt", truncation=True, max_length=512
        )
        logits = self.model(**inputs).logits
        probs = torch.softmax(logits, dim=-1)[0]
        return float(probs[self.entail_idx])


@lru_cache(maxsize=1)
def get_nli() -> NLI:
    return NLI(NLI_MODEL)
