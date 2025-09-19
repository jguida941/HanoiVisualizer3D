PY ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip

.PHONY: venv install run test clean

venv:
	$(PY) -m venv $(VENV)
	$(VENV)/bin/python -m pip install --upgrade pip

install: venv
	$(PIP) install -e '.[test]'

run:
	$(VENV)/bin/python -m HanoiVisualizer3D.main

test:
	$(VENV)/bin/python -m pytest

clean:
	rm -rf __pycache__ tests/__pycache__ .pytest_cache build dist *.egg-info
