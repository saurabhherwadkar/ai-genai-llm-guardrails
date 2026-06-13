# AI GenAI LLM Guardrails

A production-grade Python framework for implementing guardrails on both input (prompts) and output (LLM responses) of Large Language Model applications. The system is provider-agnostic, fully configurable per environment, and exposed as a FastAPI REST API.

## Features

- **Input Guardrails**: PII detection, prompt injection detection, toxic content filtering, topic restriction
- **Output Guardrails**: PII redaction, hallucination detection, content filtering, output validation
- **Provider Agnostic**: Pluggable LLM provider architecture (OpenAI, Anthropic, Mock)
- **Configurable**: YAML-based configuration with environment-specific overlays
- **Observable**: Structured logging with configurable log levels (DEBUG/INFO/WARNING/ERROR)
- **Secure**: Input validation, no code injection vectors, secrets managed via environment variables
- **Tested**: Comprehensive unit and integration test suite with high coverage

## Project Structure

```
ai-genai-llm-guardrails/
├── src/
│   └── guardrails/
│       ├── main.py                  # FastAPI application entry point
│       ├── api/                     # HTTP routes and middleware
│       │   ├── routes/
│       │   │   ├── guardrail_routes.py  # Validation endpoints
│       │   │   └── health_routes.py     # Health/readiness probes
│       │   └── middleware/
│       │       └── error_handler.py     # Global exception handling
│       ├── config/                  # Configuration management
│       │   ├── settings.py          # Pydantic settings (env-aware)
│       │   └── logging_config.py    # Structured logging setup
│       ├── core/                    # Orchestration logic
│       │   ├── engine.py            # Guardrail orchestration engine
│       │   ├── pipeline.py          # Input/Output pipeline runners
│       │   └── interfaces.py        # Abstract base classes
│       ├── guards/                  # Guard implementations
│       │   ├── input/               # Input validation guards
│       │   │   ├── pii_detector.py
│       │   │   ├── prompt_injection.py
│       │   │   ├── toxic_content.py
│       │   │   └── topic_restriction.py
│       │   └── output/              # Output validation guards
│       │       ├── pii_redactor.py
│       │       ├── hallucination.py
│       │       ├── content_filter.py
│       │       └── output_validator.py
│       ├── llm/                     # LLM provider implementations
│       │   ├── openai_provider.py
│       │   ├── anthropic_provider.py
│       │   ├── mock_provider.py
│       │   └── provider_factory.py
│       ├── models/                  # Data transfer objects
│       │   ├── requests.py
│       │   ├── responses.py
│       │   └── guard_result.py
│       └── utils/                   # Shared utilities
│           ├── text_processor.py
│           └── regex_patterns.py
├── tests/                           # Test suite
│   ├── conftest.py                  # Shared fixtures
│   ├── unit/                        # Unit tests
│   └── integration/                 # API integration tests
├── config/                          # External configuration
│   ├── application.yaml             # Base config
│   ├── application-dev.yaml         # Development overrides
│   ├── application-prod.yaml        # Production overrides
│   └── guardrails.yaml              # Guard thresholds/toggles
├── .env.example                     # Environment variable template
├── .gitignore
├── pyproject.toml                   # Project metadata and dependencies
├── requirements.txt                 # Pinned dependencies
├── Dockerfile                       # Container image definition
├── Makefile                         # Development task automation
└── README.md
```

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | >= 0.115.0 | Web framework for REST API |
| uvicorn[standard] | >= 0.32.0 | ASGI server |
| pydantic | >= 2.9.0 | Data validation and serialization |
| pydantic-settings | >= 2.6.0 | Configuration management |
| pyyaml | >= 6.0.2 | YAML config file parsing |
| structlog | >= 24.4.0 | Structured logging |
| httpx | >= 0.27.0 | Async HTTP client for LLM APIs |
| python-dotenv | >= 1.0.1 | .env file loading |
| regex | >= 2024.9.11 | Enhanced regex for PII detection |
| pytest | >= 8.3.0 | Test framework |
| pytest-asyncio | >= 0.24.0 | Async test support |
| pytest-cov | >= 6.0.0 | Coverage reporting |
| ruff | >= 0.8.0 | Linting and formatting |

## Deployment

### Prerequisites

- Python 3.11 or higher
- pip package manager

### Local Development Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd ai-genai-llm-guardrails
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows
```

3. Install dependencies (including dev tools):
```bash
make install
# or manually:
pip install -e ".[dev]"
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and settings
```

5. Run the application:
```bash
make run
# or manually:
uvicorn guardrails.main:app --host 127.0.0.1 --port 8000 --reload
```

6. Access the API documentation at: `http://localhost:8000/docs`

### Running Tests

```bash
make test
# or manually:
pytest tests/ -v
```

### Linting

```bash
make lint
make format
```

### Docker Deployment

1. Build the Docker image:
```bash
make docker-build
```

2. Run the container:
```bash
make docker-run
# or manually:
docker run -p 8000:8000 --env-file .env ai-guardrails:latest
```

### Production Deployment

1. Set `APP_ENV=prod` in your environment
2. Configure LLM provider API keys via environment variables
3. Set `LOG_LEVEL=WARNING` for production logging verbosity
4. Use the Dockerfile for containerized deployments
5. Configure your load balancer to use `/health` for liveness and `/ready` for readiness probes

## Configuration

Configuration is layered:
1. `config/application.yaml` — base defaults
2. `config/application-{APP_ENV}.yaml` — environment-specific overrides
3. `.env` file — secrets and local overrides
4. Environment variables — highest priority overrides

Guard-specific configuration lives in `config/guardrails.yaml` where you can:
- Enable/disable individual guards
- Set confidence thresholds (0.0 to 1.0)
- Configure actions (block/warn) per guard
- Define PII types to detect/redact
- Set blocked topic categories

## API Usage

### Validate Input Text

```bash
curl -X POST http://localhost:8000/api/v1/guardrails/validate \
  -H "Content-Type: application/json" \
  -d '{
    "input_text": "What is the capital of France?",
    "context": {},
    "process_with_llm": false
  }'
```

### Validate with LLM Processing

```bash
curl -X POST http://localhost:8000/api/v1/guardrails/validate \
  -H "Content-Type: application/json" \
  -d '{
    "input_text": "Explain quantum computing",
    "context": {"user_id": "user-123"},
    "process_with_llm": true
  }'
```

### Health Check

```bash
curl http://localhost:8000/health
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| APP_ENV | dev | Active environment (dev/staging/prod) |
| SERVER_HOST | 127.0.0.1 | Server bind address |
| SERVER_PORT | 8000 | Server listen port |
| LOG_LEVEL | DEBUG | Logging level |
| OPENAI_API_KEY | — | OpenAI API key (if using OpenAI provider) |
| ANTHROPIC_API_KEY | — | Anthropic API key (if using Anthropic provider) |
