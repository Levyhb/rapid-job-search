from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_session
from app.models.role import Role
from app.models.search import SearchRun
from app.schemas.company import Company, CompanyInput, ImportDocument
from app.services.company_catalog import CompanyCatalog

router = APIRouter(prefix="/api", tags=["Empresas"])


def get_catalog() -> CompanyCatalog:
    return CompanyCatalog(get_settings().companies_file)


@router.get("/companies", response_model=list[Company])
def list_companies(catalog: CompanyCatalog = Depends(get_catalog)):
    return catalog.list()


@router.post("/companies", response_model=Company, status_code=201)
def add_company(data: CompanyInput, catalog: CompanyCatalog = Depends(get_catalog)):
    return catalog.save(data)


@router.get("/companies/export")
def export_companies(catalog: CompanyCatalog = Depends(get_catalog)):
    return catalog.export()


@router.post("/companies/import/preview")
def preview_import(document: ImportDocument, catalog: CompanyCatalog = Depends(get_catalog)):
    return catalog.preview(document)


@router.post("/companies/import")
def import_companies(document: ImportDocument, catalog: CompanyCatalog = Depends(get_catalog)):
    return catalog.import_document(document)


@router.patch("/companies/{company_id}", response_model=Company)
def edit_company(
    company_id: str, data: CompanyInput, catalog: CompanyCatalog = Depends(get_catalog)
):
    return catalog.save(data, company_id)


@router.delete("/companies/{company_id}")
def remove_company(company_id: str, catalog: CompanyCatalog = Depends(get_catalog)):
    catalog.remove(company_id)
    return {"removed": True}


@router.get("/configuration/summary")
def configuration_summary(
    catalog: CompanyCatalog = Depends(get_catalog), session: Session = Depends(get_session)
):
    return {
        "company_count": len(catalog.list()),
        "selected_role_count": session.scalar(
            select(func.count()).select_from(Role).where(Role.selecionado.is_(True))
        ),
        "active_search_id": session.scalar(
            select(SearchRun.id).where(SearchRun.active_key == "active").limit(1)
        ),
        "search_available": True,
        "latest_search_id": session.scalar(
            select(SearchRun.id).order_by(SearchRun.created_at.desc()).limit(1)
        ),
    }
