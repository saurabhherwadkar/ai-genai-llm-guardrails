"""
Global error handling middleware.
Catches unhandled exceptions and returns safe, structured error responses.
Prevents internal details from leaking to clients in production.
"""

from fastapi import FastAPI, Request  # Framework types for middleware registration.
from fastapi.responses import JSONResponse  # JSON response builder for errors.
from pydantic import ValidationError  # Pydantic validation error type.

from guardrails.config.logging_config import get_logger  # Structured logger factory.
from guardrails.config.settings import get_settings  # Application settings accessor.

# Module-level logger instance for error handling events.
logger = get_logger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI application.

    Adds handlers for validation errors, value errors, and unhandled
    exceptions to return consistent structured error responses.

    Args:
        app: FastAPI application instance to register handlers on.
    """

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
        """Handle Pydantic validation errors from request parsing.

        Returns a 422 response with details about which fields failed.

        Args:
            request: The incoming HTTP request that caused the error.
            exc: The Pydantic ValidationError with field-level details.

        Returns:
            JSONResponse with 422 status and structured error body.
        """
        # Log the validation error with request path for debugging.
        logger.warning(
            "validation_error",
            path=str(request.url.path),
            error_count=len(exc.errors()),
        )
        # Return structured validation error response to the client.
        return JSONResponse(
            status_code=422,
            content={
                "status_code": 422,
                "error": "validation_error",
                "message": "Request validation failed",
                "details": {"errors": exc.errors()},
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        """Handle ValueError exceptions from business logic.

        Returns a 400 response with the error message.

        Args:
            request: The incoming HTTP request that triggered the error.
            exc: The ValueError with a descriptive error message.

        Returns:
            JSONResponse with 400 status and error description.
        """
        # Log the value error with request path for debugging.
        logger.warning(
            "value_error",
            path=str(request.url.path),
            error=str(exc),
        )
        # Return structured bad request error response to the client.
        return JSONResponse(
            status_code=400,
            content={
                "status_code": 400,
                "error": "bad_request",
                "message": str(exc),
                "details": {},
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle all unhandled exceptions as internal server errors.

        Returns a safe 500 response without exposing internal details.
        Full error details are logged server-side for debugging.

        Args:
            request: The incoming HTTP request that caused the error.
            exc: The unhandled exception caught by this handler.

        Returns:
            JSONResponse with 500 status and generic error message.
        """
        # Log the full exception details for server-side debugging.
        logger.error(
            "unhandled_exception",
            path=str(request.url.path),
            error_type=type(exc).__name__,
            error=str(exc),
            exc_info=True,
        )
        # Retrieve settings to determine if debug details should be exposed.
        settings = get_settings()
        # Include error details only in debug mode for development.
        details = {"error_type": type(exc).__name__, "message": str(exc)} if settings.debug else {}
        # Return safe internal server error response to the client.
        return JSONResponse(
            status_code=500,
            content={
                "status_code": 500,
                "error": "internal_server_error",
                "message": "An unexpected error occurred",
                "details": details,
            },
        )
