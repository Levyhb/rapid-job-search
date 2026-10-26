from contextlib import contextmanager
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.companies import get_catalog
from app.collectors.portals import CollectionReport, collect_company
from app.collectors.support import identify_platform, support_diagnostic
from app.core.database import get_session
from app.main import app
from app.models.portal_validation import PortalValidation
from app.services.company_catalog import CompanyCatalog
from app.services.portal_validation import PortalValidationService, get_validation_service


def test_detection_including_embedded_and_lookalike_hosts():
    assert identify_platform("https://alice.inhire.app/vagas") == ("inhire", "alice")
    assert identify_platform("https://afya.gupy.io/") == ("gupy", "afya")
    assert identify_platform("https://job-boards.greenhouse.io/arcoeducacao") == (
        "greenhouse",
        "arcoeducacao",
    )
    assert identify_platform("https://fake.gupy.io.example.org")[0] == "unknown"
    page = (
        '<script src="https://boards.greenhouse.io/embed/job_board/js?for=arcoeducacao"></script>'
    )
    assert identify_platform("https://example.org/carreiras", page) == (
        "greenhouse",
        "arcoeducacao",
    )


@pytest.mark.parametrize(
    ("content", "headers"),
    [
        ("<title>Just a moment...</title>", {}),
        ('<form id="challenge-form"></form>', {}),
        ("verify", {"cf-mitigated": "challenge"}),
    ],
)
def test_http_200_challenge_is_blocked_not_unsupported(content, headers):
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, text=content, headers=headers)
        )
    ) as client:
        report = collect_company(
            {"nome": "Test", "url": "https://test.gupy.io"}, lambda item: None, client=client
        )
    result = support_diagnostic(vars(report))
    assert result["support_status"] == "access_blocked"
    assert result["platform"] == "gupy"
    assert result["code"] == "access_challenge"


def test_login_redirect_is_blocked_and_normal_login_link_is_not():
    def handler(request):
        if request.url.path == "/careers":
            return httpx.Response(302, headers={"Location": "/login"})
        return httpx.Response(200, text='<input type="password"/>')

    with httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True) as client:
        report = collect_company(
            {"nome": "Test", "url": "https://example.org/careers"}, lambda item: None, client=client
        )
    assert report.reason_code == "login_required"
    assert report.resolved_url.endswith("/login")
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, text='<a href="/login">Entrar</a>')
        )
    ) as client:
        report = collect_company(
            {"nome": "Test", "url": "https://example.org"}, lambda item: None, client=client
        )
    assert report.status == "nao_suportada"


def test_redirect_to_known_platform_is_followed_and_used_for_job_links():
    def handler(request):
        if request.url.host == "careers.example.org":
            return httpx.Response(302, headers={"Location": "https://alice.inhire.app/vagas"})
        if request.url.host == "alice.inhire.app":
            return httpx.Response(200, text="<html>Portal</html>")
        return httpx.Response(
            200,
            json={
                "jobsPage": [
                    {
                        "jobId": "abc",
                        "displayName": "Dev",
                        "status": "published",
                        "workplaceType": "Remote",
                    }
                ]
            },
        )

    jobs = []
    with httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True) as client:
        report = collect_company(
            {"nome": "Test", "url": "https://careers.example.org"}, jobs.append, client=client
        )
    assert report.status == "concluida"
    assert jobs[0].url.startswith("https://alice.inhire.app/vagas/")


def test_inconclusive_network_is_not_called_incompatible_and_zero_jobs_can_be_compatible():
    report = {
        "company": "Test",
        "url": "https://example.org",
        "status": "falhou",
        "reason_code": "network_error",
        "reason": "Timeout",
    }
    result = support_diagnostic(report)
    assert result["support_status"] is None
    assert result["validation_state"] == "inconclusive"
    report.update(status="concluida", reason_code="", reason="", examined=0)
    assert support_diagnostic(report)["label"] == "Compatível"


@pytest.fixture
def validation_service():
    queue = MagicMock()
    factory = contextmanager(app.dependency_overrides[get_session])
    collector = MagicMock(
        return_value=CollectionReport(
            "Test",
            "https://test.gupy.io/",
            status="concluida",
            source="gupy",
            examined=0,
            expected=0,
        )
    )
    return PortalValidationService(factory, lambda: queue, collector), queue, collector, factory


def test_scheduling_persistence_and_stale_result_are_versioned(validation_service):
    service, queue, collector, factory = validation_service
    company = {"id": "test", "nome": "Test", "url": "https://test.gupy.io/"}
    assert service.schedule(company)["validation_state"] == "pending"
    old_token = queue.enqueue.call_args.args[2]
    updated = {**company, "url": "https://other.gupy.io/"}
    service.schedule(updated)
    new_token = queue.enqueue.call_args.args[2]
    service.run(company, old_token)
    collector.assert_not_called()
    service.run(updated, new_token)
    with factory() as session:
        record = session.get(PortalValidation, "test")
        assert record.url == updated["url"]
        assert record.result["support_status"] == "compatible"
    service.remove("test")
    service.run(updated, new_token)
    assert collector.call_count == 1


def test_queue_failure_and_unexpected_validation_failure_are_inconclusive(validation_service):
    service, queue, collector, factory = validation_service
    company = {"id": "test", "nome": "Test", "url": "https://test.gupy.io/"}
    queue.enqueue.side_effect = ConnectionError("offline")
    assert service.schedule(company)["validation_state"] == "inconclusive"
    with factory() as session:
        assert session.get(PortalValidation, "test").result["code"] == "validation_unavailable"
    queue.enqueue.side_effect = None
    service.schedule(company)
    collector.side_effect = RuntimeError("unexpected")
    service.run(company, queue.enqueue.call_args.args[2])
    with factory() as session:
        assert session.get(PortalValidation, "test").result["code"] == "validation_error"


def test_company_creation_edit_deletion_and_validation_endpoints(validation_service, tmp_path):
    service, queue, collector, factory = validation_service
    app.dependency_overrides[get_validation_service] = lambda: service
    app.dependency_overrides[get_catalog] = lambda: CompanyCatalog(tmp_path / "companies.json")
    try:
        with TestClient(app) as client:
            company = client.post(
                "/api/companies", json={"nome": "Test", "url": "https://test.gupy.io/"}
            ).json()
            company_id = company["id"]
            assert (
                client.get(f"/api/companies/{company_id}/validation").json()["validation_state"]
                == "pending"
            )
            service.run(company, queue.enqueue.call_args.args[2])
            assert (
                client.get(f"/api/companies/{company_id}/validation").json()["support_status"]
                == "compatible"
            )
            edited = client.patch(
                f"/api/companies/{company_id}", json={"nome": "Test", "url": "https://new.gupy.io/"}
            )
            assert edited.status_code == 200
            assert (
                client.get(f"/api/companies/{company_id}/validation").json()["validation_state"]
                == "pending"
            )
            assert client.post(f"/api/companies/{company_id}/validate").status_code == 202
            assert client.delete(f"/api/companies/{company_id}").status_code == 200
            with factory() as session:
                assert session.get(PortalValidation, company_id) is None
            assert client.get(f"/api/companies/{company_id}/validation").status_code == 404
            queue.enqueue.side_effect = ConnectionError("Redis offline")
            assert (
                client.post(
                    "/api/companies", json={"nome": "Nova", "url": "https://new.gupy.io/"}
                ).status_code
                == 201
            )
            assert len(client.get("/api/companies").json()) == 1
    finally:
        app.dependency_overrides.pop(get_catalog, None)
