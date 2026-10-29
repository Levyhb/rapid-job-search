import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.companies import router as companies_router
from app.api.health import router
from app.api.roles import router as roles_router
from app.api.searches import router as searches_router
from app.core.config import get_settings
from app.services.company_catalog import CatalogError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
settings = get_settings()
app = FastAPI(title=settings.app_name, version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)
app.include_router(router)
app.include_router(companies_router)
app.include_router(roles_router)
app.include_router(searches_router)


@app.exception_handler(CatalogError)
async def catalog_error_handler(request, error: CatalogError):
    return JSONResponse(status_code=error.status_code, content={"detail": str(error)})


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request, error: SQLAlchemyError):
    logging.getLogger(__name__).error("Falha no banco de dados", exc_info=error)
    return JSONResponse(
        status_code=503,
        content={"detail": ("Banco indisponível. Inicie o PostgreSQL e execute as migrações.")},
    )
