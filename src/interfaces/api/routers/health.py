"""Health check API endpoints using FastAPI routers."""

from fastapi import APIRouter, Depends

from src.infrastructure.dependencies import get_health_checker
from src.infrastructure.observability.health_checker import HealthChecker
from src.infrastructure.security import check_rate_limit
from src.interfaces.api.schemas import DetailedHealthResponse, HealthCheckDetail, HealthResponse

router = APIRouter(
    prefix="/health",
    tags=["health"],
)


@router.get("/")
async def basic_health_check(
    health_checker: HealthChecker = Depends(get_health_checker),
    _: str = Depends(check_rate_limit),
) -> HealthResponse:
    """Basic health check endpoint."""
    # Use the actual check_health method and extract basic info
    health_data = await health_checker.check_health()
    return HealthResponse(
        status=health_data["status"],
        modules=health_data.get("modules", []),
        timestamp=health_data["timestamp"],
    )


@router.get("/detailed")
async def detailed_health_check(
    health_checker: HealthChecker = Depends(get_health_checker),
    _: str = Depends(check_rate_limit),
) -> DetailedHealthResponse:
    """Detailed health check endpoint with component breakdown."""
    # Use the actual check_health method which provides detailed info
    health_data = await health_checker.check_health()

    # Convert check data to HealthCheckDetail objects
    checks = {}
    if "checks" in health_data:
        for component_name, check_data in health_data["checks"].items():
            checks[component_name] = HealthCheckDetail(
                status=check_data["status"],
                response_time_ms=check_data.get("response_time_ms", 0.0),
                error=check_data.get("error"),
            )

    return DetailedHealthResponse(
        status=health_data["status"],
        checks=checks,
        timestamp=health_data["timestamp"],
    )
