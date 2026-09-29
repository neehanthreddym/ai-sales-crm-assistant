.PHONY: install run test lint benchmark verify-llm verify-openai verify-hubspot verify-sheets

install:
	python3 -m pip install -e '.[dev]'

run:
	uvicorn app.main:app --reload --reload-dir app

test:
	python3 -m pytest -q

lint:
	python3 -m ruff check .

benchmark:
	python3 scripts/benchmark.py --count 25

verify-llm:
	python3 scripts/verify_llm.py

verify-openai:
	python3 scripts/verify_openai.py

verify-hubspot:
	python3 scripts/verify_hubspot.py

verify-sheets:
	python3 scripts/verify_sheets.py
