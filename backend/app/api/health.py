import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from redis import Redis
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import engine

router = APIRouter(tags=["Saúde"])
logger = logging.getLogger(__name__)


@router.get("/health")
def health():
    return {"status": "ok", "service": get_settings().app_name}


@router.get("/health/ready")
def readiness():
    services = {"postgres": "ok", "redis": "ok"}
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        logger.exception("PostgreSQL indisponível")
        services["postgres"] = "unavailable"
    try:
        with Redis.from_url(
            get_settings().redis_url, socket_connect_timeout=3, socket_timeout=3
        ) as client:
            client.ping()
    except Exception:
        logger.exception("Redis indisponível")
        services["redis"] = "unavailable"
    ready = all(status == "ok" for status in services.values())
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ok" if ready else "degraded", "services": services},
    )
