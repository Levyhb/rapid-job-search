from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_session
from app.models.portal_validation import PortalValidation
from app.models.role import Role
from app.models.search import SearchRun
from app.schemas.company import Company, CompanyInput, ImportDocument
from app.services.company_catalog import CompanyCatalog
from app.services.portal_validation import get_validation_service

router = APIRouter(prefix="/api", tags=["Empresas"])


def get_catalog() -> CompanyCatalog:
    return CompanyCatalog(get_settings().companies_file)


@router.get("/companies", response_model=list[Company])
def list_companies(catalog: CompanyCatalog = Depends(get_catalog)):
    return catalog.list()


@router.post("/companies", response_model=Company, status_code=201)
def add_company(
    data: CompanyInput,
    catalog: CompanyCatalog = Depends(get_catalog),
    validator=Depends(get_validation_service),
):
    company = catalog.save(data)
    validator.schedule(company.model_dump())
    return company


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
    company_id: str,
    data: CompanyInput,
    catalog: CompanyCatalog = Depends(get_catalog),
    validator=Depends(get_validation_service),
):
    company = catalog.save(data, company_id)
    validator.schedule(company.model_dump())
    return company


@router.delete("/companies/{company_id}")
def remove_company(
    company_id: str,
    catalog: CompanyCatalog = Depends(get_catalog),
    validator=Depends(get_validation_service),
):
    catalog.remove(company_id)
    validator.remove(company_id)
    return {"removed": True}


def find_company(catalog, company_id):
    company = next((item for item in catalog.list() if item.id == company_id), None)
    if not company:
        raise HTTPException(404, "Empresa não encontrada.")
    return company


@router.post("/companies/{company_id}/validate", status_code=202)
def validate_company(
    company_id: str,
    catalog: CompanyCatalog = Depends(get_catalog),
    validator=Depends(get_validation_service),
):
    return validator.schedule(find_company(catalog, company_id).model_dump())


@router.get("/companies/{company_id}/validation")
def company_validation(
    company_id: str,
    catalog: CompanyCatalog = Depends(get_catalog),
    session: Session = Depends(get_session),
):
    company = find_company(catalog, company_id)
    record = session.get(PortalValidation, company_id)
    if not record or record.url != company.url:
        return {"validation_state": "not_checked", "company_id": company_id, "url": company.url}
    return record.result or {
        "validation_state": record.state,
        "company_id": company_id,
        "url": record.url,
        "requested_at": record.requested_at,
    }


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
