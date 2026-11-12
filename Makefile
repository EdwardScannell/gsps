.PHONY: install lint format types test check example clean

install:
	python -m pip install -e ".[dev]"

lint:
	ruff check .
	ruff format --check .

format:
	ruff format .
	ruff check . --fix

types:
	python -m mypy
	python -m mypy tests --ignore-missing-imports

test:
	python -m pytest --cov=gsps --cov-report=term-missing --cov-fail-under=90

example:
	gsps validate-walk --claims examples/onepager_walk/claims.csv --track1 examples/onepager_walk/track1.csv
	-gsps ship-check --claims examples/onepager_walk/claims.csv --track1 examples/onepager_walk/track1.csv \
		--track2 examples/onepager_walk/track2.csv --page examples/onepager_walk/page.md

check: lint types test

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov build dist *.egg-info
