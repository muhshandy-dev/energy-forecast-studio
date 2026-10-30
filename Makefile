.PHONY: install data run web-data lint fmt test verify web-install web-test web-build check
install:
	python -m venv .venv && .venv/bin/pip install -e ".[dev]"
data:
	.venv/bin/energy-forecast data --source opsd
run:
	.venv/bin/energy-forecast run --source opsd
web-data:
	.venv/bin/energy-forecast export-web
lint:
	.venv/bin/ruff check . && .venv/bin/ruff format --check .
fmt:
	.venv/bin/ruff check --fix . && .venv/bin/ruff format .
test:
	.venv/bin/pytest --cov=energy_forecast --cov-report=term-missing
verify:
	.venv/bin/python tools/verify_published.py
web-install:
	cd web && npm ci
web-test:
	cd web && npm test
web-build:
	cd web && npm run build
check: lint test verify web-test web-build
