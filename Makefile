.PHONY: help up down test lint format demo

help:
	@echo "Available commands:"
	@echo "  make up       - Start all services using docker-compose"
	@echo "  make down     - Stop all services"
	@echo "  make test     - Run pytest suite"
	@echo "  make lint     - Run ruff and mypy"
	@echo "  make format   - Run ruff format"
	@echo "  make demo     - Run demo mode script"

up:
	docker compose up -d --build

down:
	docker compose down

test:
	pytest

lint:
	ruff check .
	mypy backend

format:
	ruff format .

demo:
	set PYTHONPATH=backend && python backend/app/demo.py
