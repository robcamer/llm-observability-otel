# Simple developer workflow

PYTHON?=.venv/bin/python
PIP?=.venv/bin/pip

.PHONY: help install dev test coverage run fmt clean

help:
	@echo "Targets: install | dev | test | coverage | run | clean"

install:
	$(PIP) install .

dev:
	$(PIP) install -e .[dev]

freeze:
	$(PIP) freeze > requirements.lock.txt

test:
	$(PYTHON) -m pytest

coverage:
	$(PYTHON) -m pytest --cov=src --cov-report=term-missing

run:
	$(PYTHON) -m uvicorn src.agent.app:app --reload

fmt:
	$(PYTHON) -m ruff check . || true
	$(PYTHON) -m ruff format .

clean:
	rm -rf .pytest_cache .coverage htmlcov
