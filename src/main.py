"""Main application bootstrap for FastAPI Template."""

import uvicorn

from src.infrastructure.api.app_factory import create_app, create_development_server_config
from src.infrastructure.observability import get_logger

# Create FastAPI application using factory
app = create_app()


@app.get("/status")
async def basic_status_check() -> dict[str, str | list[str]]:
    """Basic status endpoint showing system status and loaded modules (no security)."""
    return {
        "status": "healthy",
        "modules": [
            "settings",
            "logging",
            "metrics",
            "api_key_validator",
            "rate_limiter",
            "webhook_verifier",
            "health_checker",
        ],
    }


# Sample API endpoints are provided by the sample_routes router in app_factory
# /api/v1/* endpoints with proper API key authentication and rate limiting


def run_development_server() -> None:
    """Run the development server with uvicorn."""

    dev_logger = get_logger(__name__)
    dev_logger.info("Starting development server")

    # Use configuration factory for server settings
    config = create_development_server_config()
    uvicorn.run(**config)


if __name__ == "__main__":
    run_development_server()
