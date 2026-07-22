# evaluation-platform

Real-time warstwa ewaluacji dla systemów RAG. Pobiera trace'y z Langfuse, scoruje je dedykowanymi modelami i odsyła scores z powrotem do Langfuse.

Bot RAG, którego trace'y są tu scorowane, mieszka w osobnym repo: [`my-simple-rag`](../my-simple-rag).

## Wymagania

- [Docker Desktop](https://docs.docker.com/get-docker/) (z docker compose plugin)

To wszystko. Reszta działa w kontenerach.

## Uruchomienie

```bash
./bootstrap.sh
```

Skrypt:
1. Kopiuje `.env.example` → `.env` (jeśli `.env` nie istnieje)
2. Buduje obraz ewaluatora i startuje cały stack: `docker compose up --build -d`
3. Czeka aż Langfuse będzie zdrowy

Możesz też zrobić to ręcznie:

```bash
cp .env.example .env       # tylko przy pierwszym uruchomieniu
docker compose up --build -d
```

## Serwisy

| Serwis | Adres | Opis |
|---|---|---|
| `langfuse-server` | http://localhost:3000 | UI + API. Login: `admin@local.dev` / `adminpass` |
| `ollama` | http://localhost:11434 | LLM do scorera judge |
| `evaluator` | — | Polling loop; loguje do stdout |

Przy pierwszym starcie `evaluator` automatycznie ściągnie model Ollamy zdefiniowany w `JUDGE_MODEL` (domyślnie `llama3.2:3b`). Modele HuggingFace (reranker, NLI, sentiment) są cache'owane w wolumenie `hf_cache` — powtórny start jest szybki.

## Logi

```bash
make logs               # wszystkie serwisy
make evaluator-logs     # tylko evaluator
make langfuse-logs      # tylko Langfuse
```

## Sanity check (bez Langfuse)

```bash
# Wymaga lokalnego venv z zależnościami
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

make smoke              # scoruje fixture trace offline, weryfikuje że modele działają
```

## Zatrzymanie

```bash
make down               # zatrzymuje kontenery (dane woluminów zostają)
make clean              # zatrzymuje + usuwa woluminy i venv
```

## Metryki

Każdy trace z Langfuse dostaje następujące scores:

| Metryka | Zakres | Co mierzy |
|---|---|---|
| `context_relevance_mean` | 0–1 | Średnia relewancja pobranych chunków do query |
| `context_relevance_top1` | 0–1 | Relewancja najlepszego chunka |
| `retrieval_margin` | 0–1 | Jak bardzo jeden chunk dominuje nad resztą |
| `answer_relevance` | 0–1 | Czy odpowiedź trafia w intent zapytania |
| `faithfulness` | 0–1 | Czy odpowiedź jest zgodna z kontekstem (niska = halucynacja) |
| `user_sentiment_last` | -1–1 | Sentyment ostatniej wiadomości użytkownika |
| `user_sentiment_mean` | -1–1 | Średni sentyment w sesji |
| `sentiment_trend` | -2–2 | Zmiana sentymentu (ostatni − pierwszy; ujemna = pogarsza się) |
| `judge_politeness` | 0–1 | Uprzejmość odpowiedzi bota (LLM judge, opcjonalny) |
| `judge_rage_score` | 0–1 | Poziom wściekłości użytkownika (LLM judge, opcjonalny) |

Judge metrics są włączone gdy `ENABLE_LLM_JUDGE=true` w `.env`.

## Struktura

```
evaluator/
├── main.py             # polling loop
├── config.py           # konfiguracja z env
├── langfuse_client.py  # fetch traces, post scores
├── models.py           # lazy-loaded HF modele (reranker, NLI, sentiment)
├── pipeline.py         # orkiestracja scorerów
└── scorers/
    ├── retrieval.py    # context_relevance_*
    ├── generation.py   # answer_relevance, faithfulness
    ├── conversation.py # user_sentiment_*, sentiment_trend
    └── llm_judge.py    # judge_politeness, judge_rage_score (Ollama)
scripts/
├── smoke_test.py       # offline test na fixture trace
├── e2e_test.py         # end-to-end: push traces → score → verify
└── wait_for_langfuse.py
tests/fixtures/
└── sample_trace.json   # fixture używany przez smoke test
```

## Konfiguracja (.env)

Kluczowe zmienne (pełna lista w `.env.example`):

```env
ENABLE_LLM_JUDGE=true        # włącz/wyłącz Ollama judge
JUDGE_MODEL=llama3.2:3b      # model Ollamy dla judge
POLL_INTERVAL_SEC=5          # jak często sprawdzać nowe trace'y
```

Modele HF można podmienić na mniejsze warianty przez odpowiednie zmienne (`RERANKER_MODEL`, `NLI_MODEL`, `SENTIMENT_MODEL`).
