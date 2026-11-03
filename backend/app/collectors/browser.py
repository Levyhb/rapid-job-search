"""Fallback renderizado com navegação limitada e rede pública mediada por HTTPX."""

import re
import time
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urldefrag, urlsplit

import httpx
from playwright.sync_api import Error as BrowserError
from playwright.sync_api import TimeoutError as BrowserTimeout
from playwright.sync_api import sync_playwright

from app.collectors.browser_clicks import ClickNavigator, signature
from app.collectors.network import PublicHTTPTransport, UnsafeTarget, validate_target
from app.collectors.portals import (
    CollectedJob,
    CollectionReport,
    SourceProblem,
    _read,
    collect_company,
    modality,
    normalize_term,
    plain_text,
)
from app.filters.role_matching import match_title

EXTRACT = Path(__file__).with_name("browser_dom.js").read_text(encoding="utf-8")
NEXT = re.compile(
    r"^(pr[oó]xim[ao](?: p[aá]gina)?|next(?: page)?|seguinte|mais vagas|"
    r"carregar mais(?: vagas| resultados)?|load more(?: jobs| results)?|"
    r"show more(?: jobs)?)\s*[›»→]?$",
    re.I,
)
CHALLENGE = re.compile(r"just a moment|access denied|verify you are human|attention required", re.I)
TELEMETRY_HOSTS = {
    "google-analytics.com",
    "googletagmanager.com",
    "doubleclick.net",
    "nr-data.net",
}
# Widget de acessibilidade externo; não participa da listagem de anúncios.
AUXILIARY_HOSTS = {
    "equalweb.com",
    "youtube.com",
    "youtube-nocookie.com",
    "ytimg.com",
    "googlevideo.com",
}


def browser_modality(item):
    """Somente campos próprios, título explícito ou declaração; benefícios não são evidência."""
    values = [item.get("mode", ""), item.get("detail_mode", "")]
    title = item.get("title", "")
    if re.search(r"\b(remot[oa]|remote|hybrid|h[ií]brid[oa]|presencial|onsite)\b", title, re.I):
        values.append(title)
    text = plain_text(item.get("text", ""))
    declarations = re.findall(
        r"(?:modalidade(?: de trabalho)?|modelo de (?:trabalho|atua[cç][aã]o)|"
        r"regime de trabalho|work(?:place)? (?:type|model|mode))\s*[:\-]\s*([^\n.;<]{1,160})",
        text,
        re.I,
    )
    values.extend(declarations)
    normalized = [normalize_term(v) for v in values]
    modes = {
        "remote"
        if v in {"telecommute", "home office"} or v.startswith("home office ")
        else modality(v)
        for v in normalized
    }
    modes.discard("unknown")
    return (modes.pop() if len(modes) == 1 else "unknown"), " | ".join(filter(None, values))


class CollectorSession:
    def __init__(self, roles=None, seconds=120, max_pages=30, max_details=50, client=None):
        self.roles = roles
        self.seconds, self.max_pages, self.max_details = seconds, max_pages, max_details
        self.client = client
        self.owned_client = client is None
        self.engine = self.browser = None

    def __enter__(self):
        if self.client is None:
            self.client = httpx.Client(transport=PublicHTTPTransport(), trust_env=False)
        return self

    def __exit__(self, *_):
        try:
            if self.browser:
                self.browser.close()
        finally:
            if self.engine:
                self.engine.stop()
            if self.owned_client:
                self.client.close()

    def matches(self, title):
        return self.roles is None or any(
            match_title(title, r["nome"], r["variacoes"]) for r in self.roles
        )

    def collect(self, company, on_job, on_progress=lambda report: None):
        started = time.monotonic()
        self.client.cookies.clear()
        report = collect_company(company, on_job, on_progress, client=self.client)
        # Não repetir bloqueios, falhas de rede ou coletas parciais em um navegador.
        if report.status == "nao_suportada":
            report = self.render(company, on_job, on_progress)
        report.duration_seconds = round(time.monotonic() - started, 3)
        return report

    def render(self, company, on_job, on_progress):
        report = CollectionReport(company["nome"], company["url"], source="playwright")
        deadline = time.monotonic() + self.seconds
        context = None
        seen, fingerprints = set(), set()
        network_errors = []
        documents = {}
        seen_cards = set()
        previous = None
        generation = 0

        def remaining():
            value = deadline - time.monotonic()
            if value <= 0:
                raise SourceProblem("Tempo de navegação esgotado.", "parcial", "browser_limit")
            return min(value * 1000, 15000)

        def route_request(route):
            request = route.request
            host = (urlsplit(request.url).hostname or "").lower()
            telemetry = any(
                host == domain or host.endswith("." + domain)
                for domain in TELEMETRY_HOSTS | AUXILIARY_HOSTS
            )
            oracle_tracking = host.endswith(".oraclecloud.com") and re.fullmatch(
                r"/hcmRestApi/resources/[^/]+/recruitingCEUserTrackings/?",
                urlsplit(request.url).path,
            )
            if request.resource_type in {"image", "media", "font"} or telemetry or oracle_tracking:
                return route.abort()
            report.requests += 1
            if report.requests > 400 or request.method != "GET":
                if request.resource_type in {"document", "xhr", "fetch"}:
                    target = urlsplit(request.url)
                    network_errors.append(
                        f"Requisição {request.method} não suportada ou limite de rede atingido "
                        f"({target.hostname}{target.path})."
                    )
                return route.abort()
            try:
                response = documents.pop(request.url, None)
                if response is None:
                    response = _read(self.client, request.url, deadline)
                if (
                    request.resource_type == "document"
                    and urldefrag(str(response.url))[0] != request.url
                ):
                    # Chromium pode seguir redirects atendidos por fulfill sem uma nova rota.
                    # Resolver antes de goto; bloquear as demais navegações redirecionadas.
                    network_errors.append("Redirecionamento de navegação não controlada bloqueado.")
                    route.abort()
                else:
                    route.fulfill(
                        status=response.status_code,
                        headers=dict(response.headers),
                        body=response.content,
                    )
            except (SourceProblem, httpx.HTTPError, UnsafeTarget) as error:
                if request.resource_type in {"document", "xhr", "fetch", "script"}:
                    target = urlsplit(request.url)
                    network_errors.append(
                        f"{error} ({request.resource_type}: {target.hostname}{target.path})."
                    )
                route.abort()

        def navigate(page, url, timeout):
            response = _read(self.client, url, deadline)
            target = str(response.url)
            documents[urldefrag(target)[0]] = response
            page.goto(target, wait_until="domcontentloaded", timeout=timeout)

        try:
            validate_target(company["url"])
            if self.browser is None:
                self.engine = sync_playwright().start()
                self.browser = self.engine.chromium.launch(
                    headless=True,
                    timeout=remaining(),
                    # O tráfego útil é atendido pelas rotas HTTPX. Sem saída direta alternativa.
                    proxy={"server": "http://127.0.0.1:9"},
                    args=[
                        "--disable-quic",
                        "--disable-background-networking",
                        "--proxy-bypass-list=<-loopback>",
                        "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
                    ],
                )
            context = self.browser.new_context(service_workers="block", accept_downloads=False)
            context.route("**/*", route_request)
            context.route_web_socket("**/*", lambda socket: socket.close())
            context.add_init_script(
                "Object.defineProperty(globalThis,'WebTransport',"
                "{value:undefined,configurable:false});"
            )
            page = context.new_page()
            navigate(page, company["url"], remaining())
            report.resolved_url = page.url
            clicks = ClickNavigator(
                page, EXTRACT, navigate, remaining, self.wait_listing, self.advance
            )
            for step in range(self.max_pages):
                page.set_default_timeout(remaining())
                snapshot = self.wait_listing(page, remaining())
                report.resolved_url = page.url
                report.expected = snapshot.get("expected")
                current = signature(snapshot)
                if previous is not None and current[: len(previous)] != previous:
                    generation += 1
                previous = current
                if (
                    CHALLENGE.search(snapshot["title"])
                    or page.locator('input[type="password"]:visible').count()
                ):
                    raise SourceProblem(
                        "Portal exige login ou verificação de acesso.",
                        "bloqueada",
                        "access_challenge",
                    )
                fingerprint = tuple(
                    sorted(
                        (
                            j.get("title", ""),
                            j.get("url", ""),
                            (j.get("text") or "")[:200] if j.get("click") else "",
                        )
                        for j in snapshot["jobs"]
                    )
                )
                if fingerprint in fingerprints:
                    raise SourceProblem(
                        "A paginação repetiu a listagem anterior.", "parcial", "pagination_loop"
                    )
                fingerprints.add(fingerprint)
                report.batches += 1
                for index, item in enumerate(snapshot["jobs"]):
                    remaining()
                    title = str(item.get("title") or "").strip()
                    clicked = False
                    if item.get("click"):
                        key = (generation, index)
                        if key in seen_cards:
                            continue
                        seen_cards.add(key)
                        report.examined += 1
                        mode, _ = browser_modality(item)
                        if not self.matches(title) or mode in {"hybrid", "onsite"}:
                            continue
                        if report.details_opened >= self.max_details:
                            raise SourceProblem(
                                "Limite de detalhes atingido.", "parcial", "detail_limit"
                            )
                        report.details_opened += 1
                        try:
                            item = clicks.resolve(item, snapshot, index, step)
                            clicked = True
                        except SourceProblem as error:
                            report.click_failures += 1
                            if error.code == "listing_restore_failed":
                                raise
                            network_errors.append(f"{error.code}: {error}")
                            continue
                        except BrowserError:
                            report.click_failures += 1
                            network_errors.append(
                                "Falha ao abrir o detalhe de uma vaga por clique."
                            )
                            continue
                    url = urldefrag(str(item.get("url") or ""))[0]
                    if clicked:
                        url = str(item["url"])  # Preservar deep links por hash do detalhe/modal.
                    if not title or not url or url in seen:
                        continue
                    try:
                        validate_target(url)
                    except UnsafeTarget:
                        network_errors.append("Anúncio com destino não público ou inválido.")
                        continue
                    seen.add(url)
                    if not clicked:
                        report.examined += 1
                    report.resolved_jobs += 1
                    if item.get("excluded"):
                        continue
                    mode, evidence = browser_modality(item)
                    if not self.matches(title):
                        continue
                    if mode == "unknown" and not clicked:
                        if report.details_opened >= self.max_details:
                            raise SourceProblem(
                                "Limite de detalhes atingido.", "parcial", "detail_limit"
                            )
                        report.details_opened += 1
                        detail = context.new_page()
                        try:
                            detail.set_default_timeout(remaining())
                            navigate(detail, url, remaining())
                            body = detail.locator("main,article").first
                            text = body.inner_text() if body.count() else ""
                            mode, evidence = browser_modality({"title": title, "text": text})
                        except BrowserError:
                            network_errors.append("Não foi possível ler detalhes de uma vaga.")
                        finally:
                            detail.close()
                    if mode == "remote":
                        on_job(
                            CollectedJob(
                                f"browser:{url}",
                                company["nome"],
                                title,
                                url,
                                mode,
                                evidence,
                                item.get("location", ""),
                            )
                        )
                on_progress(asdict(report))
                if not snapshot["jobs"] and not snapshot["empty"]:
                    raise SourceProblem(
                        "Não foi possível reconhecer uma listagem de vagas.",
                        "nao_suportada",
                        "browser_unrecognized",
                    )
                if snapshot["empty"] and not snapshot["jobs"]:
                    break
                if not self.advance(page, snapshot, remaining(), navigate):
                    break
            else:
                raise SourceProblem("Limite de páginas atingido.", "parcial", "page_limit")
            if network_errors:
                raise SourceProblem(
                    "Coleta com falhas de leitura: " + network_errors[0],
                    "parcial",
                    "browser_network_error",
                )
            # Heurísticas não provam a cobertura de portais arbitrários.
            complete = snapshot["empty"] and not snapshot["jobs"]
            complete = complete or (
                report.expected is not None and report.examined == report.expected
            )
            report.status = "concluida" if complete else "parcial"
            if report.status == "parcial":
                report.reason = "Anúncios extraídos; cobertura total do portal não confirmada."
                report.reason_code = "browser_coverage_unverified"
                if report.expected is not None:
                    report.reason = (
                        f"Listagem lida com {report.examined} anúncios únicos; "
                        f"o site informa {report.expected}."
                    )
                    report.reason_code = "incomplete_coverage"
        except UnsafeTarget as error:
            report.status, report.reason, report.reason_code = (
                "bloqueada",
                str(error),
                "unsafe_target",
            )
        except SourceProblem as error:
            report.status, report.reason, report.reason_code = error.status, str(error), error.code
        except (BrowserError, httpx.HTTPError) as error:
            report.status = "parcial" if report.examined else "falhou"
            message = str(error).splitlines()[0][:200]
            report.reason = f"Navegação não concluída: {type(error).__name__}: {message}"
            report.reason_code = "browser_error"
        finally:
            if context:
                context.close()
        return report

    @staticmethod
    def wait_listing(page, timeout):
        # Espera por anúncios ou estado vazio explícito, sem sleeps fixos.
        try:
            page.wait_for_function(
                f"() => {{ const s=({EXTRACT})(); return s.jobs.length || s.empty; }}",
                timeout=timeout,
            )
        except BrowserTimeout:
            pass
        return page.evaluate(EXTRACT)

    @staticmethod
    def advance(page, snapshot, timeout, navigate):
        controls = page.get_by_role("button", name=NEXT).or_(page.get_by_role("link", name=NEXT))
        controls = controls.or_(
            page.locator(
                'a[rel="next"],.pagination-next a,.pagination-next button,'
                '[class*="pagination"] [aria-label="Next page"]'
            )
        )
        candidates = [
            c
            for c in controls.all()
            if c.is_visible()
            and c.is_enabled()
            and not c.evaluate('e => !!e.closest("[aria-disabled=true],[disabled],.disabled")')
        ]
        if len(candidates) > 1:
            raise SourceProblem(
                "Controles de paginação ambíguos.", "parcial", "ambiguous_pagination"
            )
        before = sorted((j.get("url", ""), j.get("title", "")) for j in snapshot["jobs"])
        if candidates:
            link = candidates[0].get_attribute("href")
            if link and not link.startswith(("#", "javascript:")):
                navigate(page, candidates[0].evaluate("e => e.href"), timeout)
            else:
                candidates[0].click(timeout=timeout)
        else:
            page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
        try:
            page.wait_for_function(
                f"before => JSON.stringify(({EXTRACT})().jobs.map(j=>[j.url||'',j.title||''])"
                ".sort()) !== JSON.stringify(before)",
                arg=before,
                timeout=min(timeout, 8000 if candidates else 2000),
            )
            return True
        except BrowserTimeout:
            if candidates:
                raise SourceProblem(
                    "A paginação não apresentou novos anúncios.", "parcial", "pagination_stalled"
                ) from None
            return False


def collect_portal(company, on_job, on_progress=lambda report: None):
    """Validação avulsa; o worker reutiliza uma sessão para várias empresas."""
    with CollectorSession() as session:
        return session.collect(company, on_job, on_progress)
