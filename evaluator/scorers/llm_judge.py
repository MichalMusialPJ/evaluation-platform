"""LLM-as-a-Judge scorers using local Ollama.

Two metrics for now:
- `judge_politeness` — evaluates the BOT's answer (0=rude, 1=perfectly polite)
- `judge_rage_score` — evaluates the USER's current message
                       (0=calm, 1=raging/abusive)

Each score comes with a plain-text reasoning stored as `score.comment` in
Langfuse, so you see WHY the judge scored it that way next to the number.
"""
from __future__ import annotations

import json
import os
import re

import ollama


JUDGE_MODEL = os.getenv("JUDGE_MODEL", "llama3.2:3b")


POLITENESS_PROMPT = """Jesteś ekspertem od oceny jakości obsługi klienta. Oceń uprzejmość i profesjonalizm poniższej odpowiedzi bota sklepu internetowego.

Skala 0-1:
- 0.0 = niegrzeczna, agresywna, obraźliwa
- 0.3 = szorstka, sucha, bez empatii
- 0.5 = neutralna, funkcjonalna
- 0.7 = uprzejma, przyjazna
- 1.0 = wyjątkowo uprzejma, empatyczna, profesjonalna

Pytanie klienta:
{query}

Odpowiedź bota:
{answer}

Odpowiedz WYŁĄCZNIE poprawnym JSON-em zgodnie ze schematem:
{{"score": <liczba od 0 do 1>, "reasoning": "<krótkie uzasadnienie po polsku, maks 2 zdania>"}}"""


RAGE_PROMPT = """Jesteś ekspertem od oceny stanu emocjonalnego klienta. Oceń poziom WŚCIEKŁOŚCI klienta w poniższej wiadomości.

Nie oceniaj ogólnego sentymentu — konkretnie **wściekłość, gniew, wrogość, obraźliwość, wulgaryzmy**. Smutek albo zniechęcenie to NIE to samo co wściekłość.

Skala 0-1:
- 0.0 = klient spokojny, uprzejmy
- 0.3 = klient lekko zniecierpliwiony
- 0.5 = klient wyraźnie sfrustrowany, ale kulturalny
- 0.7 = klient rozzłoszczony, agresywny w tonie
- 1.0 = klient wściekły, obraża bota, wulgaryzmy

Wiadomość klienta:
{query}

Odpowiedz WYŁĄCZNIE poprawnym JSON-em zgodnie ze schematem:
{{"score": <liczba od 0 do 1>, "reasoning": "<krótkie uzasadnienie po polsku, maks 2 zdania>"}}"""


def _extract_json(text: str) -> dict | None:
    """Robust JSON extraction from LLM output (fall back to regex if bare parse fails)."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return None


def _judge(prompt: str, metric_name: str) -> tuple[float, str] | None:
    """Call Ollama in JSON mode, return (score, reasoning) or None on failure."""
    try:
        response = ollama.chat(
            model=JUDGE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.0},
            format="json",  # Ollama's JSON mode — enforces valid JSON
        )
        content = response["message"]["content"]
        parsed = _extract_json(content)
        if not parsed or "score" not in parsed:
            print(f"[llm_judge] {metric_name}: failed to parse: {content[:200]!r}")
            return None
        score = float(parsed["score"])
        score = max(0.0, min(1.0, score))
        reasoning = str(parsed.get("reasoning", "")).strip()[:500]
        return score, reasoning
    except Exception as e:
        print(f"[llm_judge] {metric_name} error: {e}")
        return None


def score_llm_judge(
    query: str,
    answer: str,
) -> tuple[dict[str, float], dict[str, str]]:
    """Run judge templates over one turn. Returns (scores, comments)."""
    scores: dict[str, float] = {}
    comments: dict[str, str] = {}

    if query and answer:
        result = _judge(
            POLITENESS_PROMPT.format(query=query, answer=answer),
            "judge_politeness",
        )
        if result:
            scores["judge_politeness"], comments["judge_politeness"] = result

    if query:
        result = _judge(
            RAGE_PROMPT.format(query=query),
            "judge_rage_score",
        )
        if result:
            scores["judge_rage_score"], comments["judge_rage_score"] = result

    return scores, comments
