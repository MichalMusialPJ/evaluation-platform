# evaluation-platform

Real-time evaluation layer for RAG systems. Fetches traces from Langfuse, scores them using dedicated ML models, and posts scores back to Langfuse.

The RAG bot whose traces are scored here lives in a separate repo: [`my-simple-rag`](../my-simple-rag).

## Requirements

- [Docker Desktop](https://docs.docker.com/get-docker/) (with docker compose plugin)

That's it. Everything else runs in containers.

## Quickstart

```bash
./bootstrap.sh
```

The script:
1. Copies `.env.example` → `.env` (only on first run)
2. Builds the evaluator image and starts the full stack: `docker compose up --build -d`
3. Waits until Langfuse is healthy

Or manually:

```bash
cp .env.example .env       # first run only
docker compose up --build -d
```

## Services

| Service | Address | Description |
|---|---|---|
| `langfuse-server` | http://localhost:3000 | UI + API. Login: `admin@local.dev` / `adminpass` |
| `ollama` | http://localhost:11434 | LLM for the judge scorer |
| `evaluator` | — | Polling loop; logs to stdout |

On first start, the evaluator automatically pulls the Ollama model defined in `JUDGE_MODEL` (default: `llama3.2:3b`). HuggingFace models (reranker, NLI, sentiment) are cached in the `hf_cache` volume — subsequent starts are fast.

## Logs

```bash
make logs               # all services
make evaluator-logs     # evaluator only
make langfuse-logs      # Langfuse only
```

## Sanity check (no Langfuse needed)

```bash
# Requires a local venv with dependencies
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

make smoke              # scores a fixture trace offline, verifies models work
```

## Stop

```bash
make down               # stop containers (volumes preserved)
make clean              # stop + remove volumes and venv
```

## Metrics

Every Langfuse trace receives the following scores:

| Metric | Range | What it measures |
|---|---|---|
| `context_relevance_mean` | 0–1 | Average relevance of retrieved chunks to the query |
| `context_relevance_top1` | 0–1 | Relevance of the best chunk |
| `retrieval_margin` | 0–1 | How much the top chunk dominates the rest |
| `answer_relevance` | 0–1 | Whether the answer addresses the user's intent |
| `faithfulness` | 0–1 | Whether the answer is grounded in context (low = hallucination) |
| `user_sentiment_last` | -1–1 | Sentiment of the user's last message |
| `user_sentiment_mean` | -1–1 | Average user sentiment across the session |
| `sentiment_trend` | -2–2 | Sentiment change (last − first; negative = deteriorating) |
| `judge_politeness` | 0–1 | Politeness of the bot's answer (LLM judge, optional) |
| `judge_rage_score` | 0–1 | User rage level (LLM judge, optional) |

Judge metrics are enabled when `ENABLE_LLM_JUDGE=true` in `.env`.

## Structure

```
evaluator/
├── main.py             # polling loop
├── config.py           # config from env vars
├── langfuse_client.py  # fetch traces, post scores
├── models.py           # lazy-loaded HF models (reranker, NLI, sentiment)
├── pipeline.py         # scorer orchestration
└── scorers/
    ├── retrieval.py    # context_relevance_*
    ├── generation.py   # answer_relevance, faithfulness
    ├── conversation.py # user_sentiment_*, sentiment_trend
    └── llm_judge.py    # judge_politeness, judge_rage_score (Ollama)
scripts/
├── smoke_test.py       # offline test on a fixture trace
├── e2e_test.py         # end-to-end: push traces → score → verify
└── wait_for_langfuse.py
tests/fixtures/
└── sample_trace.json   # fixture used by smoke test
```

## Configuration (.env)

Key variables (full list in `.env.example`):

```env
ENABLE_LLM_JUDGE=true        # enable/disable Ollama judge
JUDGE_MODEL=llama3.2:3b      # Ollama model for the judge
POLL_INTERVAL_SEC=5          # how often to check for new traces
```

HF models can be swapped for smaller variants via `RERANKER_MODEL`, `NLI_MODEL`, and `SENTIMENT_MODEL`.
