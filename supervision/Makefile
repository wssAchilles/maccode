PYTHON := .venv/bin/python
PYTEST := .venv/bin/pytest
RUFF := .venv/bin/ruff
MYPY := .venv/bin/mypy

.PHONY: install test lint format typecheck demo verify

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements-dev.txt
	$(PYTHON) -m pip install numpy pydantic pydantic-settings

test:
	$(PYTEST) backend/tests

lint:
	$(RUFF) check .

format:
	$(RUFF) format .

typecheck:
	$(MYPY) backend/shared backend/domain backend/scripts

demo:
	$(PYTHON) backend/scripts/generate_demo_report.py

verify: lint typecheck test demo
