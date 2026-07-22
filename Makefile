SHELL := /usr/bin/env bash
VENV := .venv/bin
PY := $(VENV)/python

.PHONY: help bootstrap up down logs evaluator-logs langfuse-logs smoke all clean

help:
	@echo "Targets:"
	@echo "  bootstrap      — copy .env, build images, start full stack (idempotent)"
	@echo "  up             — docker compose up --build -d"
	@echo "  down           — docker compose down"
	@echo "  logs           — tail all service logs"
	@echo "  evaluator-logs — tail evaluator logs only"
	@echo "  langfuse-logs  — tail Langfuse logs only"
	@echo "  smoke          — offline scoring sanity on fixture trace (needs venv)"
	@echo "  all            — bootstrap + smoke"
	@echo "  clean          — stop containers + volumes, remove venv"

bootstrap:
	./bootstrap.sh

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

evaluator-logs:
	docker compose logs -f evaluator

langfuse-logs:
	docker compose logs -f langfuse-server

smoke:
	$(PY) scripts/smoke_test.py

all: bootstrap smoke

clean:
	docker compose down -v
	rm -rf .venv
