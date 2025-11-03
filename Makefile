# Simple developer workflow

PYTHON?=.venv/bin/python
PIP?=.venv/bin/pip

.PHONY: help install dev test coverage run clean

help:
	@echo "Targets: install | dev | test | coverage | run | clean"

install:
	$(PIP) install -r requirements.txt

dev:
	$(PIP) install -e .[dev]

test:
	$(PYTHON) -m pytest

coverage:
	$(PYTHON) -m pytest --cov=src --cov-report=term-missing

run:
	$(PYTHON) -m uvicorn src.agent.app:app --reload

clean:
	rm -rf .pytest_cache .coverage htmlcov
