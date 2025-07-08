from core.config import settings
from fastapi import APIRouter, status

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint.
    
    Returns basic application information and status.
    Useful for monitoring, load balancers, and container orchestration.
    """
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "api_base": settings.API_STR
    }


@router.get("/ping", status_code=status.HTTP_200_OK)
async def ping():
    """
    Simple ping endpoint.
    
    Returns a minimal response for basic connectivity tests.
    """
    return {"ping": "pong"}