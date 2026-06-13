"""
FastAPI application entry point.
Configures and assembles the complete application with routes,
middleware, and startup/shutdown lifecycle hooks.
"""

from collections.abc import AsyncGenerator  # Type for async generator functions.
from contextlib import asynccontextmanager  # Async context manager for lifespan.

from fastapi import FastAPI  # Web framework application class.

from guardrails.api.middleware.error_handler import register_error_handlers  # Error handling.
from guardrails.api.routes.guardrail_routes import router as guardrail_router  # Guard routes.
from guardrails.api.routes.health_routes import router as health_router  # Health routes.
from guardrails.config.logging_config import configure_logging, get_logger  # Logging setup.
from guardrails.config.settings import get_settings  # Application settings accessor.


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown.

    Configures logging and performs initialization on startup.
    Handles graceful cleanup on shutdown.

    Args:
        app: The FastAPI application instance being managed.

    Yields:
        None — control is passed to the application for request handling.
    """
    # Configure structured logging before any log events are emitted.
    configure_logging()
    # Get logger after logging is configured for startup messages.
    startup_logger = get_logger(__name__)
    # Log application startup with version and environment information.
    settings = get_settings()
    startup_logger.info(
        "application_starting",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
    )
    # Yield control to the application for request processing.
    yield
    # Log graceful shutdown of the application.
    startup_logger.info("application_shutting_down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance.

    Assembles all routes, middleware, and configuration into a
    fully-configured application ready to serve requests.

    Returns:
        Configured FastAPI application instance.
    """
    # Load application settings for metadata configuration.
    settings = get_settings()
    # Create the FastAPI application with metadata and lifespan.
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Production-grade LLM guardrails for input and output validation",
        lifespan=lifespan,
    )
    # Register global error handlers for consistent error responses.
    register_error_handlers(app)
    # Include health check routes at the root path level.
    app.include_router(health_router)
    # Include guardrail validation routes under /api/v1 prefix.
    app.include_router(guardrail_router)
    # Return the fully configured application instance.
    return app


# Create the application instance for ASGI server usage.
app = create_app()
