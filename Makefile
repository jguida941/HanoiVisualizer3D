PY ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip

.PHONY: venv install run test clean

venv:
	$(PY) -m venv $(VENV)
	$(VENV)/bin/python -m pip install --upgrade pip

install: venv
	# Install runtime dependencies (no editable install; no code changes required)
	$(PIP) install -r requirements.txt

run: venv
	# Launch the app directly from this folder
	$(VENV)/bin/python main.py

test: venv
	# Ensure test dependencies are present and make current folder importable as a package
	$(PIP) install -r requirements-dev.txt
	PYTHONPATH=$(PWD)/.. $(VENV)/bin/python -m pytest

clean:
	rm -rf __pycache__ tests/__pycache__ .pytest_cache build dist *.egg-info
