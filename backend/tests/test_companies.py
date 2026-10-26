import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.companies import get_catalog
from app.main import app
from app.schemas.company import CompanyInput
from app.services.company_catalog import CompanyCatalog
from app.services.portal_validation import get_validation_service


@pytest.fixture
def catalog_path(tmp_path):
    return tmp_path / "data" / "empresas.json"


@pytest.fixture
def client(catalog_path):
    app.dependency_overrides[get_catalog] = lambda: CompanyCatalog(catalog_path)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_catalog, None)


def test_crud_is_persisted_and_keeps_identity(client, catalog_path):
    assert client.get("/api/companies").json() == []
    response = client.post(
        "/api/companies", json={"nome": "Ação Tech", "url": "https://example.org/jobs?country=br"}
    )
    assert response.status_code == 201
    company_id = response.json()["id"]
    assert CompanyCatalog(catalog_path).list()[0].nome == "Ação Tech"
    edited = client.patch(
        f"/api/companies/{company_id}",
        json={"nome": "Ação Atualizada", "url": "https://example.org/carreiras"},
    )
    assert edited.status_code == 200
    assert edited.json()["id"] == company_id
    assert (
        json.loads(catalog_path.read_text(encoding="utf-8"))["empresas"][0]["nome"]
        == "Ação Atualizada"
    )
    assert client.get("/api/configuration/summary").json()["company_count"] == 1
    assert client.delete(f"/api/companies/{company_id}").status_code == 200
    assert CompanyCatalog(catalog_path).list() == []
    assert client.delete(f"/api/companies/{company_id}").status_code == 404


def test_duplicates_and_invalid_urls_do_not_modify_file(client, catalog_path):
    data = {"nome": " Ação Tech ", "url": "https://example.org"}
    assert client.post("/api/companies", json=data).status_code == 201
    before = catalog_path.read_bytes()
    assert (
        client.post(
            "/api/companies", json={"nome": "acao tech", "url": "https://EXAMPLE.org/"}
        ).status_code
        == 409
    )
    for url in ["javascript:alert(1)", "ftp://example.org", "https://user:pass@example.org", "bad"]:
        assert client.post("/api/companies", json={"nome": "Outra", "url": url}).status_code == 422
    assert catalog_path.read_bytes() == before


def test_batch_persists_together_and_schedules_each_portal(client, catalog_path):
    validator = MagicMock()
    previous = app.dependency_overrides[get_validation_service]
    app.dependency_overrides[get_validation_service] = lambda: validator
    entries = [
        {"nome": "Empresa A", "url": "https://example.org/a"},
        {"nome": "Empresa B", "url": "https://example.org/b"},
    ]
    try:
        response = client.post("/api/companies/batch", json={"empresas": entries})
        assert response.status_code == 201
        saved = response.json()
        assert len({item["id"] for item in saved}) == 2
        assert [item.model_dump() for item in CompanyCatalog(catalog_path).list()] == saved
        assert validator.schedule.call_count == 2
        assert [call.args[0] for call in validator.schedule.call_args_list] == saved
    finally:
        app.dependency_overrides[get_validation_service] = previous


def test_batch_invalid_or_duplicate_never_saves_partially(client, catalog_path):
    existing = {"nome": "Ação Tech", "url": "https://example.org/"}
    client.post("/api/companies", json=existing)
    before = catalog_path.read_bytes()
    valid = {"nome": "Nova", "url": "https://example.org/nova"}
    for entries, status in [
        ([], 422),
        ([valid, {"nome": "Inválida", "url": "ftp://example.org"}], 422),
        ([valid, {"nome": "acao tech", "url": "https://EXAMPLE.org"}], 409),
        ([valid, valid], 409),
    ]:
        response = client.post("/api/companies/batch", json={"empresas": entries})
        assert response.status_code == status
        assert catalog_path.read_bytes() == before


def test_import_review_roundtrip_and_duplicate_skip(client):
    document = {
        "versao": 1,
        "empresas": [
            {"nome": "Empresa A", "url": "https://example.org/a"},
            {"nome": "Empresa A", "url": "https://example.org/a"},
            {"nome": "Empresa B", "url": "https://example.org/b?tenant=2"},
        ],
    }
    preview = client.post("/api/companies/import/preview", json=document)
    assert preview.status_code == 200
    assert len(preview.json()["empresas"]) == 2
    assert preview.json()["duplicadas"] == 1
    assert client.get("/api/companies").json() == []
    assert client.post("/api/companies/import", json=document).json() == {
        "importadas": 2,
        "duplicadas": 1,
    }
    exported = client.get("/api/companies/export").json()
    assert exported["versao"] == 1
    assert "id" not in exported["empresas"][0]
    assert exported["empresas"][1]["url"].endswith("?tenant=2")
    assert client.post("/api/companies/import", json=exported).json() == {
        "importadas": 0,
        "duplicadas": 2,
    }
    for company in client.get("/api/companies").json():
        client.delete(f"/api/companies/{company['id']}")
    assert client.post("/api/companies/import", json=exported).json()["importadas"] == 2
    assert client.get("/api/companies/export").json() == exported


def test_import_errors_are_reviewable_and_atomic(client, catalog_path):
    document = {
        "versao": 1,
        "empresas": [
            {"nome": "Válida", "url": "https://example.org"},
            {"nome": "Inválida", "url": "bad"},
        ],
    }
    preview = client.post("/api/companies/import/preview", json=document).json()
    assert preview["erros"][0]["linha"] == 2
    assert len(preview["empresas"]) == 1
    assert client.post("/api/companies/import", json=document).status_code == 422
    assert not catalog_path.exists()
    assert (
        client.post("/api/companies/import", json={"versao": 2, "empresas": []}).status_code == 422
    )
    assert (
        client.post(
            "/api/companies/import", json={"versao": 1, "empresas": preview["empresas"]}
        ).json()["importadas"]
        == 1
    )


def test_corrupt_file_is_never_overwritten(client, catalog_path):
    catalog_path.parent.mkdir(parents=True)
    catalog_path.write_text("{broken", encoding="utf-8")
    assert client.get("/api/companies").status_code == 503
    assert (
        client.post(
            "/api/companies", json={"nome": "Nova", "url": "https://example.org"}
        ).status_code
        == 503
    )
    assert catalog_path.read_text(encoding="utf-8") == "{broken"


def _create_in_process(path, index):
    CompanyCatalog(Path(path)).save(
        CompanyInput(nome=f"Empresa {index}", url=f"https://example.org/{index}")
    )


def test_concurrent_processes_do_not_lose_companies(catalog_path):
    with ProcessPoolExecutor(max_workers=3) as pool:
        list(pool.map(_create_in_process, [str(catalog_path)] * 12, range(12)))
    assert len(CompanyCatalog(catalog_path).list()) == 12
    assert not list(catalog_path.parent.glob("*.tmp"))
