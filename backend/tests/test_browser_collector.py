import json
from dataclasses import asdict
from threading import Lock, get_ident

import httpx
import pytest

from app.collectors.browser import CollectorSession, browser_modality
from app.collectors.events import collect_events
from app.collectors.portals import CollectionReport

COMPANY = {"nome": "Exemplo", "url": "https://example.org/careers"}
ROLES = [{"nome": "Desenvolvedor", "variacoes": ["Dev", "Backend"]}]


def card(number, title="Desenvolvedor Backend", mode="Remoto"):
    return (
        f'<article class="job-card"><a href="/jobs/{number}"><h3>{title}</h3></a>'
        f'<span class="modality">{mode}</span></article>'
    )


def collect(html, routes=None, **options):
    calls, jobs, progress = [], [], []
    routes = routes or {}

    def respond(request):
        calls.append(str(request.url))
        value = routes.get(request.url.path, html if request.url.path == "/careers" else "")
        if isinstance(value, httpx.Response):
            return value
        return httpx.Response(200, text=value, headers={"content-type": "text/html; charset=utf-8"})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with CollectorSession(roles=ROLES, client=client, seconds=25, **options) as session:
            report = session.collect(COMPANY, jobs.append, progress.append)
    return report, jobs, progress, calls


def test_dynamic_fetch_load_more_dedup_and_remote_filter():
    html = """<main id="list"></main><button id="more" onclick="load()">Carregar mais</button>
    <script>let n=0; async function load(){ n++;
    const response=await fetch('/batch'+n); document.querySelector('main').innerHTML +=
    await response.text(); if(n===2)document.querySelector('button').remove(); }
    setTimeout(load,50);</script>"""
    report, jobs, progress, calls = collect(
        html,
        {
            "/batch1": card(1) + card(2, mode="Híbrido"),
            "/batch2": card(1) + card(3, "Dev Java") + card(4, "DevOps", "Remoto"),
        },
    )
    assert [job.title for job in jobs] == ["Desenvolvedor Backend", "Dev Java"]
    assert report.examined == 4 and report.batches == 2 and report.details_opened == 0
    assert report.status == "parcial" and report.reason_code == "browser_coverage_unverified"
    assert progress and report.requests >= 3 and report.duration_seconds > 0
    assert not any("/jobs/" in url for url in calls)


def test_next_page_and_unknown_details_only_for_matching_roles():
    first = card(1, mode="") + card(2, "Analista Financeiro", "")
    first += '<a href="/page2">Next page</a>'
    report, jobs, _, calls = collect(
        first,
        {
            "/jobs/1": "<main><p>Modalidade: Remoto</p></main>",
            "/page2": card(3, mode="Presencial"),
        },
    )
    assert len(jobs) == 1 and report.details_opened == 1 and report.batches == 2
    assert not any("/jobs/2" in url for url in calls)


def test_jsonld_remote_and_explicit_empty_state():
    data = {
        "@type": "JobPosting",
        "title": "Dev Java",
        "url": "https://example.org/jobs/1",
        "jobLocationType": "TELECOMMUTE",
    }
    report, jobs, _, _ = collect(
        '<script type="application/ld+json">' + json.dumps(data) + "</script>"
    )
    assert len(jobs) == 1 and report.details_opened == 0
    empty, jobs, _, _ = collect("<main><p>Nenhuma vaga disponível</p></main>")
    assert empty.status == "concluida" and not jobs
    assert asdict(report)["source"] == "playwright"


def test_stalled_pagination_and_page_limit_report_partial():
    report, jobs, _, _ = collect(card(1) + "<button>Mais vagas</button>")
    assert len(jobs) == 1 and report.reason_code == "pagination_stalled"
    report, _, _, _ = collect(card(1) + '<a href="/p2">Próxima</a>', {"/p2": card(2)}, max_pages=1)
    assert report.reason_code == "page_limit"


def test_private_links_and_subrequests_never_reach_transport():
    html = card(1) + '<script>fetch("http://127.0.0.1/private").catch(()=>{});</script>'
    html += '<article><a href="http://169.254.169.254/jobs/1">Dev Java</a></article>'
    report, jobs, _, calls = collect(html)
    assert len(jobs) == 1 and report.status == "parcial"
    assert all("127.0.0.1" not in url and "169.254" not in url for url in calls)


def test_http_block_never_starts_browser():
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(403))) as client:
        with CollectorSession(client=client) as session:
            report = session.collect(COMPANY, lambda job: pytest.fail("blocked source emitted job"))
            assert session.browser is None and report.status == "bloqueada"


def test_known_public_feed_uses_http_without_starting_browser():
    props = {"props": {"pageProps": {"careerPage": {"id": 1}, "jobs": []}}}
    html = '<script id="__NEXT_DATA__">' + json.dumps(props) + "</script>0 jobs found"
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, text=html))
    ) as client:
        with CollectorSession(client=client) as session:
            report = session.collect(
                {"nome": "Test", "url": "https://test.gupy.io/"}, lambda j: None
            )
            assert report.status == "concluida" and session.browser is None


def test_discarded_analytics_does_not_mark_complete_listing_as_failed():
    html = '<main><p class="jobs-total">1 jobs available</p>' + card(1) + "</main>"
    html += """<script>fetch('https://www.google-analytics.com/g/collect',
      {method:'POST',mode:'no-cors',body:'test'}).catch(()=>{});</script>"""
    report, jobs, _, calls = collect(html)
    assert report.status == "concluida" and len(jobs) == 1
    assert not any("google-analytics" in url for url in calls)


def test_oracle_tracking_is_discarded_without_hiding_job_api_failures():
    html = '<main><p class="jobs-total">1 jobs available</p>' + card(1) + "</main>"
    html += """<script>fetch('https://test.oraclecloud.com/hcmRestApi/resources/latest/' +
      'recruitingCEUserTrackings',{method:'POST',mode:'no-cors',body:'test'}).catch(()=>{});
      fetch('/actual-jobs',{method:'POST',body:'test'}).catch(()=>{});</script>"""
    report, jobs, _, calls = collect(html)
    assert len(jobs) == 1
    assert report.status == "parcial" and report.reason_code == "browser_network_error"
    assert "actual-jobs" in report.reason and "UserTrackings" not in report.reason
    assert not any("UserTrackings" in url or "actual-jobs" in url for url in calls)


def test_auxiliary_widget_failure_does_not_invalidate_explicit_empty_listing():
    html = "<main><p>Nenhuma vaga encontrada</p></main>"
    html += """<script>fetch('https://cdn.equalweb.com/assets/data/lang.json')
      .catch(()=>{});</script>"""
    report, jobs, _, calls = collect(html)
    assert report.status == "concluida" and not jobs
    assert not any("equalweb" in url for url in calls)


def test_scroll_appends_jobs_and_redirect_keeps_relative_links():
    html = "<main>" + card(1) + '</main><div style="height:3000px"></div>'
    html += """<script>addEventListener('scroll',()=>{
      if(!window.added){window.added=true;document.querySelector('main').innerHTML +=
      '<article class="job-card"><a href="/jobs/2"><h3>Dev Java Remoto</h3></a></article>';}
    });</script>"""
    report, jobs, _, _ = collect(html)
    assert len(jobs) == 2 and report.batches == 2
    redirect = httpx.Response(302, headers={"location": "/team/"})
    report, jobs, _, _ = collect(
        redirect,
        {
            "/team/": '<main><article><a href="position">Dev Java Remoto</a></article></main>',
        },
    )
    assert report.resolved_url == "https://example.org/team/", asdict(report)
    assert jobs[0].url == "https://example.org/team/position"


def test_unknown_page_and_detail_limit_are_reported_honestly():
    report, jobs, _, _ = collect("<main><p>Conheça nossa empresa</p></main>")
    assert report.reason_code == "browser_unrecognized" and not jobs
    report, jobs, _, _ = collect(card(1, mode=""), max_details=0)
    assert report.reason_code == "detail_limit" and not jobs


@pytest.mark.parametrize(
    ("item", "expected"),
    [
        ({"text": "Benefícios: auxílio home office e trabalho remoto"}, "unknown"),
        ({"mode": "Híbrido", "title": "Dev Remoto"}, "unknown"),
        ({"mode": "Not remote"}, "onsite"),
        ({"text": "Workplace type: Fully remote"}, "remote"),
        ({"text": "Modelo de trabalho: Presencial"}, "onsite"),
    ],
)
def test_remote_requires_explicit_consistent_evidence(item, expected):
    assert browser_modality(item)[0] == expected


def test_concurrent_events_keep_browser_sessions_in_their_threads_and_isolate_failures():
    owners, lock = [], Lock()

    class Session:
        def __init__(self, roles):
            self.thread = get_ident()

        def __enter__(self):
            with lock:
                owners.append(self.thread)
            return self

        def __exit__(self, *args):
            assert get_ident() == self.thread

        def collect(self, company, on_job, on_progress):
            assert get_ident() == self.thread
            if company["nome"] == "Falha":
                raise ValueError("fixture")
            on_progress({"url": company["url"]})
            return CollectionReport(company["nome"], company["url"], status="concluida")

    companies = [
        COMPANY,
        {"nome": "Falha", "url": "https://example.org/bad"},
        {"nome": "Outra", "url": "https://example.org/other"},
    ]
    events = list(collect_events(companies, ROLES, session_factory=Session))
    reports = [payload[1] for kind, payload in events if kind == "report"]
    assert len(owners) == 2 and len(reports) == 3
    assert sum(report.status == "concluida" for report in reports) == 2
    assert next(r for r in reports if r.company == "Falha").reason_code == "collector_error"


def test_accordion_announcements_with_explicit_count_and_hidden_links():
    html = '<main><p class="jobs-total">2 vagas disponiveis.</p>'
    for n, mode in [(1, "Remoto"), (2, "Hibrido")]:
        html += (
            f'<li class="accordion-item"><h3><button aria-controls="panel{n}">'
            f'Desenvolvedor Java {mode}</button></h3><div id="panel{n}" hidden>'
            f'<a href="/announcements/{n}">Confira esta vaga completa</a></div></li>'
        )
    report, jobs, _, _ = collect(html + "</main>")
    assert report.expected == 2 and report.examined == 2 and report.status == "concluida"
    assert len(jobs) == 1 and report.details_opened == 0


def test_hash_route_is_preserved_for_client_side_navigation():
    jobs = []

    def respond(request):
        return httpx.Response(
            200,
            text='<main><a href="/jobs/1">Dev Java Remoto</a></main>',
            headers={"content-type": "text/html; charset=utf-8"},
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with CollectorSession(client=client, roles=ROLES, seconds=15) as session:
            report = session.collect(
                {"nome": "SPA", "url": "https://example.org/#careers"}, jobs.append
            )
    assert len(jobs) == 1 and report.resolved_url.endswith("#careers")


def test_cyclic_and_ambiguous_pagination_preserve_jobs_and_report_partial():
    first = card(1) + '<a href="/p2">Next</a>'
    second = card(2) + '<a href="/careers">Next</a>'
    report, jobs, _, _ = collect(first, {"/p2": second})
    assert len(jobs) == 2 and report.reason_code == "pagination_loop"
    report, jobs, _, _ = collect(card(1) + "<button>Next</button><button>Mais vagas</button>")
    assert len(jobs) == 1 and report.reason_code == "ambiguous_pagination"


def test_navigation_budget_exhaustion_is_partial():
    with CollectorSession(seconds=0) as session:
        report = session.render(COMPANY, lambda job: None, lambda report: None)
        assert report.status == "parcial" and report.reason_code == "browser_limit"
        assert session.browser is None


def clickable_card(number, action, mode="Remoto", title=None):
    return (
        f'<article class="job-card"><h3>{title or f"Dev Backend {number}"}</h3>'
        f'<span class="modality">{mode}</span>'
        f'<button onclick="{action}">Ver vaga</button></article>'
    )


@pytest.mark.parametrize("popup", [False, True])
def test_click_only_card_captures_navigation_or_new_tab_url_and_continues(popup):
    html = "<main>"
    for n in [1, 2]:
        action = f"window.open('/jobs/{n}','_blank')" if popup else f"location.href='/jobs/{n}'"
        html += clickable_card(n, action)
    html += "</main>"
    routes = {
        f"/jobs/{n}": f"<main><h1>Dev Backend {n}</h1><p>Modalidade: Remoto</p></main>"
        for n in [1, 2]
    }
    report, jobs, _, _ = collect(html, routes)
    assert [j.url for j in jobs] == ["https://example.org/jobs/1", "https://example.org/jobs/2"]
    assert report.resolved_jobs == 2 and report.click_failures == 0
    assert report.details_opened == 2 and report.examined == 2


def test_spa_click_restores_pagination_even_if_back_resets_to_first_page():
    html = """<main></main><script>
    let current=1;
    function render(){document.querySelector('main').innerHTML=
      '<p class="jobs-total">2 jobs available</p><article class="job-card"><h3>Dev Backend '+
      current+'</h3><span class="modality">Remoto</span>'+
      '<button onclick="openJob()">Ver vaga</button></article>'+
      (current===1?'<button onclick="current=2;render()">Next</button>':'');}
    function openJob(){history.pushState({},'','/jobs/'+current);
      document.querySelector('main').innerHTML='<h1>Dev Backend</h1><p>Modalidade: Remoto</p>';}
    onpopstate=()=>{current=1;render()};render();</script>"""
    report, jobs, _, _ = collect(html)
    assert len(jobs) == 2 and {j.url for j in jobs} == {
        "https://example.org/jobs/1",
        "https://example.org/jobs/2",
    }
    assert report.examined == 2 and report.batches == 2 and report.status == "concluida"


@pytest.mark.parametrize("hash_url", [False, True])
def test_click_opens_modal_with_shareable_link_or_hash_and_closes_before_next_job(hash_url):
    html = "<main>"
    for n in [1, 2]:
        change_url = f"history.pushState({{}},'', '#job={n}');" if hash_url else ""
        html += clickable_card(n, change_url + f"document.getElementById('d{n}').showModal()")
        html += (
            f'<dialog id="d{n}"><h2>Dev Backend {n}</h2>'
            "<p>Modalidade: Remoto</p>"
            f'<a href="/jobs/{n}">Ver vaga completa</a>'
            f"<button onclick=\"document.getElementById('d{n}').close()\">Fechar</button></dialog>"
        )
    report, jobs, _, _ = collect(html + "</main>")
    expected = [
        f"https://example.org/careers#job={n}" if hash_url else f"https://example.org/jobs/{n}"
        for n in [1, 2]
    ]
    assert [j.url for j in jobs] == expected
    assert report.click_failures == 0 and report.details_opened == 2


def test_modal_without_shareable_url_reports_failure_instead_of_inventing_job_link():
    from app.collectors.support import collection_failed

    html = clickable_card(1, "document.getElementById('d').showModal()")
    html += """<dialog id="d"><h2>Dev Backend 1</h2><p>Modalidade: Remoto</p>
      <button onclick="document.getElementById('d').close()">Fechar</button></dialog>"""
    report, jobs, _, _ = collect(html)
    assert not jobs and report.click_failures == 1
    assert "click_without_url" in report.reason and collection_failed(asdict(report))


def test_click_candidates_exclude_application_actions_and_unselected_roles():
    html = clickable_card(1, "fetch('/not-to-click')", title="Analista Financeiro")
    html += """<article class="job-card"><h3>Dev Backend</h3>
      <button onclick="fetch('/application')">Candidatar-se</button></article>"""
    report, jobs, _, calls = collect(html)
    assert not jobs and report.details_opened == 0
    assert not any("/application" in url or "/not-to-click" in url for url in calls)


def test_title_button_inside_open_shadow_root_is_detected_and_clicked():
    html = """<div id="host"></div><script>
      document.querySelector('#host').attachShadow({mode:'open'}).innerHTML=
      `<article class="job-card"><h3><button onclick="location.href='/jobs/1'">
      Dev Backend</button></h3><p class="modality">Remoto</p></article>`;</script>"""
    report, jobs, _, _ = collect(html, {"/jobs/1": "<main><h1>Dev Backend</h1></main>"})
    assert len(jobs) == 1 and jobs[0].url == "https://example.org/jobs/1"
    assert report.resolved_jobs == 1 and not report.click_failures


def test_click_navigation_to_private_target_never_reaches_http_transport():
    html = clickable_card(1, "location.href='http://127.0.0.1/jobs/private'")
    report, jobs, _, calls = collect(html)
    assert not jobs and report.status != "concluida"
    assert not any("127.0.0.1" in url for url in calls)


def test_portuguese_card_title_is_separate_from_apply_cta_and_filters_are_preserved():
    html = '<main><p id="vagas-count">2 vagas encontradas</p><ul>'
    for n, title, mode, hidden in [
        (1, "Desenvolvedor Java", "Remote", ""),
        (2, "[Banco de Talentos] Desenvolvedor Java", "Remote", ""),
        (3, "Desenvolvedor Python", "Hybrid", "hidden"),
    ]:
        html += (
            f'<li class="vaga-card" data-modelo="{mode}" {hidden}>'
            f'<a href="/vagas/{n}"><span class="vaga-area">Desenvolvimento</span>'
            f'<span class="vaga-titulo">{title}</span>'
            '<span class="vaga-ver">Ver vaga e candidatar-se</span></a></li>'
        )
    report, jobs, _, calls = collect(html + "</ul></main>")
    assert [j.title for j in jobs] == ["Desenvolvedor Java"]
    assert jobs[0].modality_original == "Remote"
    assert report.examined == report.expected == 2 and report.status == "concluida"
    assert report.details_opened == 0 and not any("/vagas/" in url for url in calls)


def test_job_table_reads_animation_hidden_rows_but_respects_real_hidden_filters():
    html = '<main><section id="jobs"><h4>Nossas vagas (2)</h4>'
    for n, mode, hidden in [
        (1, "Remoto", ""),
        (2, "Presencial", ""),
        (3, "Remoto", "hidden"),
        (4, "Remoto", 'aria-hidden="true"'),
        (5, "Remoto", 'style="display:none"'),
    ]:
        html += (
            f'<div {hidden}><div class="wow fadeInUp" style="visibility:hidden">'
            f'<table><tr><td><a href="/vagas/job/{n}">Dev Backend {n}</a></td>'
            f"<td>Efetivo</td><td><b>{mode}</b></td><td>Brasil</td></tr></table></div></div>"
        )
    html += "</section><p>Benefícios: auxílio home office e ajuda para trabalho remoto</p></main>"
    report, jobs, _, calls = collect(html)
    assert [j.title for j in jobs] == ["Dev Backend 1"]
    assert jobs[0].location == "Brasil" and jobs[0].modality_original == "Remoto"
    assert report.examined == report.expected == 2 and report.status == "concluida"
    assert report.details_opened == 0 and len(calls) == 2


def test_announced_count_mismatch_keeps_results_with_honest_coverage_warning():
    html = '<main><p id="jobs-count">2 jobs available</p>' + card(1) + "</main>"
    report, jobs, _, _ = collect(html)
    assert len(jobs) == 1 and report.examined == 1 and report.expected == 2
    assert report.status == "parcial" and report.reason_code == "incomplete_coverage"
