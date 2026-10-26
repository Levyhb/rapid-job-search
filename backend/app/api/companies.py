from fastapi import APIRouter, Depends

from app.core.config import get_settings
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
def configuration_summary(catalog: CompanyCatalog = Depends(get_catalog)):
    # Ainda não há cadastro de cargos nem execuções de busca implementados.
    return {
        "company_count": len(catalog.list()),
        "selected_role_count": 0,
        "active_search_id": None,
    }
