from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.api.searches import run_payload
from app.collectors.support import collection_failed


@pytest.mark.parametrize(
    ("status", "examined", "failed"),
    [
        ("concluida", 0, False),
        ("concluida", 10, False),
        ("consultando", 0, False),
        ("parcial", 12, False),
        ("parcial", 0, True),
        ("falhou", 0, True),
        ("bloqueada", 0, True),
        ("nao_suportada", 0, True),
    ],
)
def test_only_actual_collection_failures_enter_the_error_counter(status, examined, failed):
    assert collection_failed({"status": status, "examined": examined}) is failed


def test_old_saved_validations_are_reclassified_without_modifying_historical_reports():
    reports = []
    for name, status, examined in [
        ("Lida pelo navegador", "parcial", 12),
        ("Sem vagas", "concluida", 0),
        ("Bloqueada", "bloqueada", 0),
        ("Formato desconhecido", "nao_suportada", 0),
    ]:
        reports.append(
            {
                "company": name,
                "url": "https://example.org/" + str(len(reports)),
                "status": status,
                "examined": examined,
                "source": "playwright",
            }
        )
    reports[0]["validation"] = {
        "id": "old",
        "company": reports[0]["company"],
        "collection_status": "parcial",
        "has_failure": True,
        "checked_at": "2026-11-03T10:00:00Z",
        "code": "browser_coverage_unverified",
        "coverage": {"examined": 12},
    }
    run = SimpleNamespace(id="test", status="completed", reports=reports)
    result = run_payload(run, Mock(scalar=Mock(return_value=4)))
    assert result["found_count"] == 4
    assert len(result["source_validations"]) == 4
    assert [item["company"] for item in result["diagnostics"]] == [
        "Bloqueada",
        "Formato desconhecido",
    ]
    read = result["source_validations"][0]
    assert read["has_warning"] is True and read["has_failure"] is False
    assert read["checked_at"] == "2026-11-03T10:00:00Z"
    assert reports[0]["validation"]["has_failure"] is True
