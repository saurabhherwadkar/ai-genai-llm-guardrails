.PHONY: install run test lint format clean docker-build docker-run

# Install all dependencies including dev
install:
	pip install -e ".[dev]"

# Run the FastAPI application server
run:
	uvicorn guardrails.main:app --host 0.0.0.0 --port 8000 --reload

# Run all unit and integration tests with coverage
test:
	pytest tests/ -v

# Run ruff linter to check code quality
lint:
	ruff check src/ tests/

# Auto-format code using ruff
format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

# Remove build artifacts and caches
clean:
	rm -rf __pycache__ .pytest_cache .coverage htmlcov dist build *.egg-info .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Build Docker image
docker-build:
	docker build -t ai-guardrails:latest .

# Run Docker container
docker-run:
	docker run -p 8000:8000 --env-file .env ai-guardrails:latest
