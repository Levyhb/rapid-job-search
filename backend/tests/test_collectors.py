import json

import httpx

from app.collectors.portals import collect_company, greenhouse_mode, modality


def test_gupy_full_public_feed_includes_jobs_beyond_first_ui_page():
    items = [
        {"id": index, "title": f"Dev {index}", "workplace": {"workplaceType": "remote"}}
        for index in range(23)
    ]
    props = {"props": {"pageProps": {"careerPage": {"id": 1}, "jobs": items}}}
    content = (
        '<script id="__NEXT_DATA__" type="application/json">'
        + json.dumps(props)
        + "</script>23 jobs found"
    )
    jobs, batches = [], []
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text=content))
    ) as client:
        report = collect_company(
            {"nome": "Test", "url": "https://test.gupy.io/"}, jobs.append, batches.append, client
        )
    assert report.status == "concluida"
    assert report.examined == 23
    assert report.batches == 3
    assert jobs[-1].url.endswith("/jobs/22")
    assert all(job.modality == "remote" for job in jobs)


def test_missing_pages_and_limits_are_partial_not_complete():
    props = {
        "props": {
            "pageProps": {
                "careerPage": {"id": 1},
                "jobs": [{"id": n, "title": "Dev"} for n in range(12)],
            }
        }
    }
    content = f'<script id="__NEXT_DATA__">{json.dumps(props)}</script>30 jobs found'
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text=content))
    ) as client:
        report = collect_company(
            {"nome": "Test", "url": "https://test.gupy.io/"}, lambda item: None, client=client
        )
        assert report.status == "parcial" and report.expected == 30
        limited = collect_company(
            {"nome": "Test", "url": "https://test.gupy.io/"},
            lambda item: None,
            client=client,
            max_jobs=2,
        )
        assert limited.status == "parcial" and limited.examined == 2


def test_inhire_public_feed_and_identity():
    def handler(request):
        if request.url.host == "alice.inhire.app":
            return httpx.Response(200, text="<html>Portal Alice</html>")
        assert request.headers["x-tenant"] == "alice"
        return httpx.Response(
            200,
            json={
                "jobsPage": [
                    {
                        "jobId": "abc",
                        "displayName": "Dev Backend",
                        "status": "published",
                        "workplaceType": "Remote",
                        "location": "Brasil",
                    }
                ]
            },
        )

    jobs = []
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = collect_company(
            {"nome": "Alice", "url": "https://alice.inhire.app/vagas"}, jobs.append, client=client
        )
    assert report.status == "concluida"
    assert jobs[0].identity == "inhire:alice:abc"
    assert jobs[0].location == "Brasil"


def test_embedded_greenhouse_and_incomplete_feed():
    def handler(request):
        if request.url.host == "example.org":
            return httpx.Response(
                200,
                text='<script src="https://boards.greenhouse.io/embed/job_board/js?for=test"></script>',
            )
        return httpx.Response(
            200,
            json={
                "meta": {"total": 2},
                "jobs": [
                    {
                        "id": 1,
                        "title": "Dev",
                        "absolute_url": "https://example.org/jobs/1",
                        "location": {"name": "Remoto"},
                    }
                ],
            },
        )

    jobs = []
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = collect_company(
            {"nome": "Test", "url": "https://example.org/carreiras"}, jobs.append, client=client
        )
    assert report.status == "parcial"
    assert report.examined == 1 and jobs[0].modality == "remote"


def test_remote_evidence_not_benefits_and_conflicts_are_unknown():
    assert modality("Híbrido") == "hybrid"
    assert modality("not remote") == "onsite"
    assert (
        greenhouse_mode(
            {
                "location": {"name": "São Paulo"},
                "content": "Benefícios: auxílio para trabalho remoto.",
            }
        )[0]
        == "unknown"
    )
    assert (
        greenhouse_mode(
            {"location": {"name": "Brasil"}, "content": "<p>Modelo de trabalho: Remoto</p>"}
        )[0]
        == "remote"
    )
    assert (
        greenhouse_mode({"location": {"name": "Remote"}, "content": "Modalidade: Híbrido"})[0]
        == "unknown"
    )


def test_blocks_unsupported_and_invalid_data_are_not_zero_successes():
    for status_code, content, expected in [
        (403, "denied", "bloqueada"),
        (200, "<html>generic</html>", "nao_suportada"),
    ]:
        with httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(status_code, text=content))
        ) as client:
            report = collect_company(
                {"nome": "Test", "url": "https://example.org"}, lambda item: None, client=client
            )
        assert report.status == expected


def test_malformed_listing_keeps_valid_jobs_and_marks_partial():
    props = {
        "props": {
            "pageProps": {
                "careerPage": {"id": 1},
                "jobs": [
                    {"id": 1, "title": "Dev", "workplace": {"workplaceType": "remote"}},
                    {"id": 2},
                ],
            }
        }
    }
    content = '<script id="__NEXT_DATA__">' + json.dumps(props) + "</script>"
    jobs = []
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text=content))
    ) as client:
        report = collect_company(
            {"nome": "Test", "url": "https://test.gupy.io/"}, jobs.append, client=client
        )
    assert len(jobs) == 1 and report.status == "parcial"
