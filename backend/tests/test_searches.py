import time
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.companies import get_catalog
from app.api.searches import get_queue
from app.collectors.portals import CollectedJob, CollectionReport
from app.core.database import get_session
from app.main import app
from app.models.search import SearchJob, SearchRun
from app.schemas.company import CompanyInput
from app.services.company_catalog import CompanyCatalog
from app.workers.searches import run_search


@pytest.fixture
def configured(tmp_path):
    catalog = CompanyCatalog(tmp_path / "companies.json")
    catalog.save(CompanyInput(nome="Falha", url="https://bad.gupy.io"))
    catalog.save(CompanyInput(nome="Boa", url="https://good.gupy.io"))
    queue = MagicMock()
    app.dependency_overrides[get_catalog] = lambda: catalog
    app.dependency_overrides[get_queue] = lambda: queue
    with (
        TestClient(app) as client,
        patch("app.api.searches.Worker.all", return_value=[MagicMock()]),
    ):
        client.post("/api/roles", json={"nome": "Desenvolvedor", "variacoes": ["Dev"]})
        yield client, queue, catalog
    app.dependency_overrides.pop(get_catalog, None)
    app.dependency_overrides.pop(get_queue, None)


def collector(company, on_job, progress):
    if company["nome"] == "Falha":
        return CollectionReport("Falha", company["url"], status="bloqueada", reason="HTTP 403")
    for identity, title, mode in [
        ("one", "Dev Backend", "remote"),
        ("one", "Dev Backend", "remote"),
        ("two", "Dev Java", "hybrid"),
        ("three", "DevOps", "remote"),
        ("four", "Dev Frontend", "unknown"),
    ]:
        on_job(
            CollectedJob(identity, "Boa", title, "https://example.org/jobs/" + identity, mode, mode)
        )
    return CollectionReport(
        "Boa", company["url"], status="concluida", batches=1, examined=5, expected=5
    )


def test_snapshot_queue_worker_progress_dedup_failures_and_result(configured):
    client, queue, catalog = configured
    started = client.post("/api/searches")
    assert started.status_code == 202
    run_id = started.json()["id"]
    queue.enqueue.assert_called_once()
    assert client.post("/api/searches").status_code == 409
    # Alterar os cargos depois não muda a configuração da execução.
    role_id = client.get("/api/roles").json()[0]["id"]
    client.patch(f"/api/roles/{role_id}/selection", json={"selecionado": False})
    factory = contextmanager(app.dependency_overrides[get_session])
    run_search(run_id, factory, collector)
    status = client.get(f"/api/searches/{run_id}").json()
    assert status["status"] == "completed" and status["found_count"] == 1
    assert status["diagnostics"][0]["company"] == "Falha"
    assert status["diagnostics"][0]["label"] == "Acesso bloqueado"
    assert [item["label"] for item in status["source_validations"]] == [
        "Acesso bloqueado",
        "Compatível",
    ]
    assert all(item["url"] and item["checked_at"] for item in status["source_validations"])
    jobs = client.get(f"/api/searches/{run_id}/jobs").json()
    assert jobs["items"][0]["title"] == "Dev Backend"
    assert jobs["items"][0]["modality"] == "remote"
    assert jobs["total"] == 1
    run_search(run_id, factory, collector)
    assert client.get(f"/api/searches/{run_id}").json()["found_count"] == 1


def test_queue_failure_does_not_leave_active_execution(configured):
    client, queue, _ = configured
    queue.enqueue.side_effect = RuntimeError("offline")
    assert client.post("/api/searches").status_code == 503
    assert client.get("/api/configuration/summary").json()["active_search_id"] is None


def test_pagination_and_worker_crash_recovery(configured):
    client, queue, _ = configured
    run_id = client.post("/api/searches").json()["id"]
    factory = contextmanager(app.dependency_overrides[get_session])
    with factory() as session:
        run = session.get(SearchRun, run_id)
        run.updated_at = time.time() - 40
        for index in range(23):
            session.add(
                SearchJob(
                    run_id=run_id,
                    identity=str(index),
                    company="Test",
                    title=f"Dev {index}",
                    url="https://example.org",
                    modality="remote",
                    modality_original="Remoto",
                    location="Brasil",
                    matches=[],
                )
            )
        session.commit()
    with patch("app.api.searches.Job.fetch") as job:
        job.return_value.get_status.return_value = "failed"
        assert client.get(f"/api/searches/{run_id}").json()["status"] == "interrupted"
    assert len(client.get(f"/api/searches/{run_id}/jobs?page=2").json()["items"]) == 3
    assert client.get(f"/api/searches/{run_id}/jobs?page=0").status_code == 422
    assert client.get("/api/searches/missing").status_code == 404
