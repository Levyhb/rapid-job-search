"""Coletores de fontes públicas verificadas: InHire, Gupy e Greenhouse."""

import json
import re
import time
import zlib
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from urllib.parse import urlsplit

import httpx

from app.collectors.network import (
    PublicHTTPTransport,
    UnsafeTarget,
    request_budget,
    validate_target,
)
from app.collectors.support import identify_platform
from app.filters.role_matching import normalize_term


@dataclass
class CollectedJob:
    identity: str
    company: str
    title: str
    url: str
    modality: str
    modality_original: str
    location: str = ""


@dataclass
class CollectionReport:
    company: str
    url: str
    status: str = "consultando"
    source: str = ""
    batches: int = 0
    examined: int = 0
    expected: int | None = None
    reason: str = ""
    reason_code: str = ""
    resolved_url: str = ""


class SourceProblem(Exception):
    def __init__(self, message, status="falhou", code="unsupported_format", resolved_url=""):
        super().__init__(message)
        self.status = status
        self.code = code
        self.resolved_url = resolved_url


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain_text(value):
    import html

    parser = TextParser()
    parser.feed(html.unescape(value or ""))
    return "\n".join(parser.parts)


def modality(value):
    value = normalize_term(str(value or ""))
    if re.search(r"\b(hybrid|hibrido|hibrida)\b", value):
        return "hybrid"
    if re.search(r"\b(remote friendly|not fully remote|remoto parcial|partially remote)\b", value):
        return "unknown"
    if re.search(r"\b(non remote|not remote|nao remoto|presencial|onsite|on site)\b", value):
        return "onsite"
    if re.search(r"\b(remote|remoto|remota|telecommute)\b", value):
        return "remote"
    return "unknown"


def greenhouse_mode(item):
    # Só campos de modalidade/localidade ou uma declaração explícita no anúncio.
    evidence = str(item.get("location", {}).get("name", ""))
    mode = modality(evidence)
    declarations = []
    for line in plain_text(item.get("content", "")).splitlines():
        line = line.strip()
        if re.match(
            r"^(?:modelo de trabalho|modelo de atua[cç][aã]o|modalidade|"
            r"regime de trabalho|formato de trabalho)\s*[:\-]",
            line,
            re.I,
        ):
            declarations.append(line)
    for metadata in item.get("metadata") or []:
        label = normalize_term(str(metadata.get("name", "")))
        if label in {"modalidade", "modelo de trabalho", "workplace type", "workplace_type"}:
            declarations.append(str(metadata.get("value", "")))
    known = [(modality(value), value) for value in declarations if modality(value) != "unknown"]
    modes = {value for value, _ in known}
    if mode != "unknown":
        modes.add(mode)
    if len(modes) > 1:
        return "unknown", " | ".join([evidence, *declarations])
    if known:
        return known[0]
    return mode, evidence


MAX_RESPONSE_BYTES = 10 * 1024 * 1024
COLLECTION_SECONDS = 180


def _remaining(deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise SourceProblem("Tempo total de coleta esgotado.", "parcial", "collection_limit")
    return min(25, remaining)


def _limited_body(response, deadline):
    buffered = response.is_stream_consumed  # MockTransport pode entregar conteúdo já lido.
    encoding = "identity" if buffered else response.headers.get("content-encoding", "identity")
    encoding = encoding.strip().lower()
    if encoding not in {"identity", "gzip"}:
        raise SourceProblem(
            "Codificação da resposta não suportada.", "parcial", "response_encoding"
        )
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS) if encoding == "gzip" else None
    body = bytearray()
    received = 0
    chunks = [response.content] if buffered else response.iter_raw(chunk_size=65536)
    try:
        for chunk in chunks:
            _remaining(deadline)
            received += len(chunk)
            if received > MAX_RESPONSE_BYTES:
                raise SourceProblem(
                    "Resposta excedeu o limite de 10 MB.", "parcial", "response_limit"
                )
            decoded = (
                decoder.decompress(chunk, MAX_RESPONSE_BYTES - len(body) + 1)
                if decoder else chunk
            )
            if len(body) + len(decoded) > MAX_RESPONSE_BYTES:
                raise SourceProblem(
                    "Resposta excedeu o limite de 10 MB.", "parcial", "response_limit"
                )
            body.extend(decoded)
        _remaining(deadline)
        if decoder and (not decoder.eof or decoder.unused_data):
            raise httpx.DecodingError("Resposta gzip incompleta ou com membros adicionais.")
    except zlib.error as error:
        raise httpx.DecodingError("Resposta gzip inválida.") from error
    return bytes(body)


def _public_get(client, url, deadline, **kwargs):
    for redirect in range(6):
        target = validate_target(url)
        headers = {**kwargs.pop("headers", {}), "Accept-Encoding": "identity"}
        with request_budget(deadline), client.stream(
            "GET", target, follow_redirects=False,
            timeout=_remaining(deadline), headers=headers, **kwargs,
        ) as response:
            if not response.is_redirect or "location" not in response.headers:
                if response.status_code in {401, 403, 429}:
                    raise SourceProblem(
                        f"Acesso limitado pela fonte (HTTP {response.status_code}).",
                        "bloqueada", f"http_{response.status_code}", str(response.url),
                    )
                response.raise_for_status()
                length = response.headers.get("content-length", "")
                if length.isdigit() and int(length) > MAX_RESPONSE_BYTES:
                    raise SourceProblem(
                        "Resposta excedeu o limite de 10 MB.", "parcial", "response_limit"
                    )
                body = _limited_body(response, deadline)
                result_headers = dict(response.headers)
                for name in ("content-encoding", "content-length", "transfer-encoding"):
                    result_headers.pop(name, None)
                return httpx.Response(
                    response.status_code, content=body, headers=result_headers,
                    request=response.request,
                )
            try:
                next_url = response.url.join(response.headers["location"])
            except httpx.InvalidURL as error:
                raise UnsafeTarget("Redirecionamento inválido.") from error
        if redirect == 5:
            raise SourceProblem(
                "Limite de redirecionamentos atingido.", "bloqueada", "redirect_limit"
            )
        # Parâmetros pertencem apenas à URL inicial, e headers de integração
        # não devem atravessar origens diferentes.
        kwargs.pop("params", None)
        if (target.scheme, target.host, target.port) != (
            next_url.scheme, next_url.host, next_url.port
        ):
            headers = {"Accept-Encoding": "identity"}
        kwargs["headers"] = headers
        url = next_url


def _read(client, url, deadline, **kwargs):
    for attempt in range(2):
        try:
            response = _public_get(client, url, deadline, **kwargs)
            title = re.search(r"<title[^>]*>(.*?)</title>", response.text[:200000], re.I | re.S)
            title_text = normalize_term(title.group(1)) if title else ""
            challenge = (
                response.headers.get("cf-mitigated") == "challenge"
                or title_text
                in {
                    "just a moment",
                    "access denied",
                    "verify you are human",
                    "attention required cloudflare",
                }
                or bool(
                    re.search(
                        r'<form[^>]+id=[\'"]challenge-form[\'"]', response.text[:200000], re.I
                    )
                )
            )
            login = bool(
                re.search(r"/(?:login|signin|sign_in|auth)(?:/|$)", response.url.path)
            ) and bool(
                re.search(r'<input[^>]+type=[\'"]password[\'"]', response.text[:200000], re.I)
            )
            if challenge or login:
                raise SourceProblem(
                    "A fonte exige verificação de acesso ou login.",
                    "bloqueada",
                    "access_challenge" if challenge else "login_required",
                    str(response.url),
                )
            return response
        except UnsafeTarget as error:
            raise SourceProblem(str(error), "bloqueada", "unsafe_target") from error
        except (httpx.TimeoutException, httpx.TransportError):
            _remaining(deadline)
            if attempt:
                raise
            time.sleep(min(0.5, _remaining(deadline)))


def _load(company, client, report, deadline):
    url = company["url"]
    report.source, tenant = identify_platform(url)
    page = _read(client, url, deadline)
    report.resolved_url = str(page.url)
    report.source, tenant = identify_platform(report.resolved_url, page.text)
    if report.source == "inhire":
        data = _read(
            client, "https://api.inhire.app/job-posts/public/pages", deadline,
            headers={"x-tenant": tenant},
        ).json()
        items = data.get("jobsPage")
        if not isinstance(items, list):
            raise SourceProblem("Formato público InHire não reconhecido.", "nao_suportada")
        report.expected = len(items)
        return _convert(items, company, report, tenant, deadline)
    if report.source == "gupy":
        match = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', page.text, re.S)
        if not match:
            raise SourceProblem(
                "Dados públicos Gupy não encontrados; formato exige nova validação.",
                "nao_suportada",
            )
        props = json.loads(match.group(1))["props"]["pageProps"]
        items = props.get("jobs")
        if not isinstance(items, list) or not props.get("careerPage"):
            raise SourceProblem("Listagem pública Gupy não reconhecida.", "nao_suportada")
        report.expected = len(items)
        visible_count = re.search(r"(\d+)\s+(?:jobs found|vagas encontradas)", page.text)
        if visible_count:
            report.expected = int(visible_count.group(1))
        return _convert(items, company, report, tenant, deadline)
    token = tenant if report.source == "greenhouse" else None
    if not token or not re.fullmatch(r"[a-zA-Z0-9_-]+", token):
        raise SourceProblem(
            "Portal sem formato público reconhecido ou com integração ambígua.",
            "nao_suportada",
            "unsupported_portal",
        )
    report.source = "greenhouse"
    data = _read(
        client,
        f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs",
        deadline,
        params={"content": "true"},
    ).json()
    items = data.get("jobs")
    if not isinstance(items, list):
        raise SourceProblem("Listagem Greenhouse não reconhecida.", "nao_suportada")
    report.expected = data.get("meta", {}).get("total", len(items))
    return _convert(items, company, report, token, deadline)


def _convert(items, company, report, tenant, deadline):
    result = []
    host = urlsplit(report.resolved_url or company["url"]).hostname
    for item in items:
        _remaining(deadline)
        try:
            if report.source == "inhire":
                if item.get("status") != "published":
                    report.expected -= 1
                    continue
                job_id = str(item["jobId"])
                title = item["displayName"].strip()
                slug = re.sub(r"[^a-z0-9]+", "-", normalize_term(title)).strip("-")
                original = str(item.get("workplaceType", ""))
                job = CollectedJob(
                    f"inhire:{tenant}:{job_id}",
                    company["nome"],
                    title,
                    f"https://{host}/vagas/{job_id}/{slug}",
                    modality(original),
                    original,
                    str(item.get("location", "")),
                )
            elif report.source == "gupy":
                original = str((item.get("workplace") or {}).get("workplaceType", ""))
                job = CollectedJob(
                    f"gupy:{tenant}:{item['id']}",
                    company["nome"],
                    item["title"],
                    f"https://{host}/jobs/{item['id']}",
                    modality(original),
                    original,
                    json.dumps(
                        (item.get("workplace") or {}).get("address", {}), ensure_ascii=False
                    ),
                )
            else:
                mode, evidence = greenhouse_mode(item)
                job = CollectedJob(
                    f"greenhouse:{tenant}:{item['id']}",
                    company["nome"],
                    item["title"],
                    item["absolute_url"],
                    mode,
                    evidence,
                    str(item.get("location", {}).get("name", "")),
                )
            if not isinstance(job.title, str) or not isinstance(job.url, str):
                raise ValueError("Título ou URL inválidos")
            result.append(job)
        except (AttributeError, ValueError, KeyError, TypeError):
            report.reason_code = "invalid_job_data"
            report.status, report.reason = (
                "parcial",
                "Parte dos anúncios não pôde ser interpretada.",
            )
    return result


def collect_company(company, on_job, on_progress=lambda report: None, client=None, max_jobs=10000):
    report = CollectionReport(company["nome"], company["url"])
    started = time.monotonic()
    owned = client is None
    client = client or httpx.Client(
        timeout=25,
        transport=PublicHTTPTransport(),
        trust_env=False,
        follow_redirects=False,
        headers={"User-Agent": "RapidJobSearch/0.1 (personal career search)"},
    )
    try:
        try:
            items = _load(company, client, report, started + COLLECTION_SECONDS)
        except SourceProblem as error:
            report.status, report.reason = error.status, str(error)
            report.reason_code = error.code
            report.resolved_url = error.resolved_url or report.resolved_url
            return report
        except (httpx.HTTPError, AttributeError, ValueError, KeyError, TypeError) as error:
            report.reason_code = (
                "network_error" if isinstance(error, httpx.HTTPError) else "parse_error"
            )
            report.status, report.reason = (
                "falhou",
                f"Falha de leitura da fonte: {type(error).__name__}: {error}",
            )
            return report
        seen = set()
        for item in items:
            if time.monotonic() - started > COLLECTION_SECONDS or report.examined >= max_jobs:
                report.status, report.reason = "parcial", "Limite de tempo ou quantidade atingido."
                report.reason_code = "collection_limit"
                break
            if item.identity in seen:
                continue
            if not item.title.strip() or urlsplit(item.url).scheme not in {"http", "https"}:
                report.status, report.reason = "parcial", "Anúncio sem título ou link válido."
                report.reason_code = "invalid_job_data"
                continue
            seen.add(item.identity)
            on_job(item)
            report.examined += 1
            if report.examined % 10 == 0:
                report.batches += 1
                on_progress(asdict(report))
        if report.examined % 10 or not report.batches:
            report.batches += 1
        if report.status == "consultando":
            report.status = "concluida" if report.examined == report.expected else "parcial"
            if report.status == "parcial":
                report.reason = "Total processado difere do total informado pela fonte."
                report.reason_code = "incomplete_coverage"
        return report
    finally:
        if owned:
            client.close()
