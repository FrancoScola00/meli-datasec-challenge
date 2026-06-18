# MeLi DataSec Challenge — task runner (Linux / macOS graders).
# On Windows use run.ps1 with the same targets (see README).
PY  ?= .venv/bin/python
PIP ?= $(PY) -m pip

.PHONY: help install test c1 c2 c3-verify c4-demo

help:
	@echo "Targets: install | test | c1 | c2 | c3-verify | c4-demo"

install:
	python3.12 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

test:
	$(PY) -m pytest -v

c1:
	$(PY) solution_minesweeper.py

c2:
	$(PY) solution_best_in_genre.py Action

# Requires a running MySQL 8 with a root user. Loads the seed + runs the graded query.
c3-verify:
	mysql -u root < tests/seed_and_check.sql

# Live LLM call — requires OPENROUTER_API_KEY in the environment (see challenge4/.env.example).
c4-demo:
	$(PY) challenge4/demo_live.py --text "Ayudame a debuggear el deploy de prod: AWS key AKIAIOSFODNN7EXAMPLE, server 10.2.4.8, escribime a devops@meli.com"
