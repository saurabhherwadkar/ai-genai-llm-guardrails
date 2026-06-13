"""
Logging configuration module.
Sets up structured logging using structlog with configurable levels and formats.
Supports JSON output for production and pretty console output for development.
"""

import logging  # Standard library logging framework.
import sys  # System-specific parameters for stdout access.

import structlog  # Structured logging library for rich log events.

from guardrails.config.settings import get_settings  # Application settings accessor.


def configure_logging() -> None:
    """Configure structured logging for the entire application.

    Sets up structlog processors, formatters, and log level
    based on application settings. Call once at application startup.
    """
    # Retrieve current application settings for log configuration.
    settings = get_settings()
    # Convert string log level to numeric logging constant.
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    # Define shared processors that run on every log event.
    shared_processors: list[structlog.types.Processor] = [
        # Add the logger name to each log event for source identification.
        structlog.stdlib.add_logger_name,
        # Add the log level string to each event for severity filtering.
        structlog.stdlib.add_log_level,
        # Add a UTC timestamp to every log event for temporal ordering.
        structlog.processors.TimeStamper(fmt="iso"),
        # Merge any extra keyword arguments into the log event dictionary.
        structlog.processors.StackInfoRenderer(),
        # Format exception tracebacks for readability in log output.
        structlog.processors.format_exc_info,
        # Decode byte strings to unicode for consistent text handling.
        structlog.processors.UnicodeDecoder(),
    ]
    # Select renderer based on configured format (json vs console).
    if settings.log_format == "json":
        # Use JSON renderer for machine-parseable structured log output.
        renderer = structlog.processors.JSONRenderer()
    else:
        # Use console renderer with colors for human-readable dev output.
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    # Configure structlog with the assembled processor pipeline.
    structlog.configure(
        # Set the processor chain that transforms each log event.
        processors=[
            # Filter log events below the configured minimum severity level.
            structlog.stdlib.filter_by_level,
            # Add shared processors for consistent event enrichment.
            *shared_processors,
            # Bridge structlog events to stdlib logging for compatibility.
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        # Use standard library logger as the underlying logger implementation.
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Cache logger instances on first access for performance.
        cache_logger_on_first_use=True,
    )
    # Create a formatter that applies structlog processors to stdlib logs.
    formatter = structlog.stdlib.ProcessorFormatter(
        # Apply the chosen renderer (JSON or console) as final formatter.
        processor=renderer,
        # Apply shared processors to events from non-structlog loggers too.
        foreign_pre_chain=shared_processors,
    )
    # Configure the root logger handler for stdout output.
    handler = logging.StreamHandler(sys.stdout)
    # Attach the structlog formatter to the stdout handler.
    handler.setFormatter(formatter)
    # Get the root logger to configure application-wide logging.
    root_logger = logging.getLogger()
    # Remove any existing handlers to prevent duplicate log output.
    root_logger.handlers.clear()
    # Add our configured handler as the sole output destination.
    root_logger.addHandler(handler)
    # Set the minimum log level for the root logger from settings.
    root_logger.setLevel(log_level)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Create a named structured logger instance.

    Args:
        name: Logger name, typically the module's __name__.

    Returns:
        Bound structlog logger instance with the given name.
    """
    # Return a structlog logger bound to the specified module name.
    return structlog.get_logger(name)
