"""Config resolved from env (with sensible defaults)."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).parent.parent / ".env")


RERANKER_MODEL = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
SENTIMENT_MODEL = os.getenv(
    "SENTIMENT_MODEL", "cardiffnlp/twitter-xlm-roberta-base-sentiment"
)
NLI_MODEL = os.getenv(
    "NLI_MODEL", "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
)

POLL_INTERVAL_SEC = int(os.getenv("POLL_INTERVAL_SEC", "10"))

LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
