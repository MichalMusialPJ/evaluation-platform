FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY evaluator/ ./evaluator/
COPY scripts/wait_for_langfuse.py ./scripts/

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# HuggingFace models cache — mount a volume here to persist across restarts
ENV HF_HOME=/cache/huggingface

ENTRYPOINT ["./entrypoint.sh"]
