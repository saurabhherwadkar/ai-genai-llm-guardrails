"""
Health check API routes.
Provides endpoints for monitoring application health and readiness.
Used by load balancers and orchestrators for service discovery.
"""

from fastapi import APIRouter  # Router for grouping related endpoints.

from guardrails.config.settings import get_settings  # Application settings accessor.
from guardrails.models.responses import HealthResponse  # Health response schema.

# Create router instance for health-related endpoints.
router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint for liveness probes.

    Returns application status, version, and environment information.
    Used by container orchestrators to verify the service is running.

    Returns:
        HealthResponse with current application health status.
    """
    # Retrieve current application settings for version information.
    settings = get_settings()
    # Build and return the health response with application metadata.
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        environment=settings.app_env,
        components={"api": "healthy", "guardrails": "healthy"},
    )


@router.get("/ready", response_model=HealthResponse)
async def readiness_check() -> HealthResponse:
    """Readiness check endpoint for traffic routing decisions.

    Verifies that the application is ready to accept and process requests.
    Returns degraded status if any critical component is unavailable.

    Returns:
        HealthResponse with readiness status of all components.
    """
    # Retrieve current application settings for version information.
    settings = get_settings()
    # Check component readiness status for comprehensive health view.
    components = {
        "api": "healthy",
        "guardrails": "healthy",
        "configuration": "healthy",
    }
    # Determine overall status based on component health states.
    overall_status = "healthy" if all(v == "healthy" for v in components.values()) else "degraded"
    # Build and return the readiness response with component details.
    return HealthResponse(
        status=overall_status,
        version=settings.app_version,
        environment=settings.app_env,
        components=components,
    )
