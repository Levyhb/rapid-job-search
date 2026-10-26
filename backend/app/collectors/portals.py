"""Coletores de fontes públicas verificadas: InHire, Gupy e Greenhouse."""

import html
import json
import re
import time
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit

import httpx

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


class SourceProblem(Exception):
    def __init__(self, message, status="falhou"):
        super().__init__(message)
        self.status = status


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain_text(value):
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


def _read(client, url, **kwargs):
    for attempt in range(2):
        try:
            response = client.get(url, **kwargs)
            if response.status_code in {401, 403, 429}:
                raise SourceProblem(
                    f"Acesso limitado pela fonte (HTTP {response.status_code}).", "bloqueada"
                )
            response.raise_for_status()
            if len(response.content) > 10 * 1024 * 1024:
                raise SourceProblem("Resposta excedeu o limite de 10 MB.", "parcial")
            return response
        except (httpx.TimeoutException, httpx.TransportError):
            if attempt:
                raise
            time.sleep(0.5)


def _load(company, client, report):
    url = company["url"]
    host = (urlsplit(url).hostname or "").lower()
    tenant = host.split(".")[0]
    if host.endswith(".inhire.app"):
        report.source = "inhire"
        data = _read(
            client, "https://api.inhire.app/job-posts/public/pages", headers={"x-tenant": tenant}
        ).json()
        items = data.get("jobsPage")
        if not isinstance(items, list):
            raise SourceProblem("Formato público InHire não reconhecido.", "nao_suportada")
        report.expected = len(items)
        return _convert(items, company, report, tenant)
    page = _read(client, url)
    if host.endswith(".gupy.io"):
        report.source = "gupy"
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
        return _convert(items, company, report, tenant)
    token = None
    if host in {"boards.greenhouse.io", "job-boards.greenhouse.io"}:
        token = urlsplit(url).path.strip("/").split("/")[0]
    else:
        embedded = re.findall(
            r'https://boards\.greenhouse\.io/embed/job_board/js\?([^"<>\s]+)', page.text
        )
        tokens = {parse_qs(html.unescape(value)).get("for", [""])[0] for value in embedded}
        tokens.discard("")
        if len(tokens) == 1:
            token = tokens.pop()
    if not token or not re.fullmatch(r"[a-zA-Z0-9_-]+", token):
        raise SourceProblem(
            "Portal ainda sem coletor validado (InHire, Gupy ou Greenhouse).", "nao_suportada"
        )
    report.source = "greenhouse"
    data = _read(
        client,
        f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs",
        params={"content": "true"},
    ).json()
    items = data.get("jobs")
    if not isinstance(items, list):
        raise SourceProblem("Listagem Greenhouse não reconhecida.", "nao_suportada")
    report.expected = data.get("meta", {}).get("total", len(items))
    return _convert(items, company, report, token)


def _convert(items, company, report, tenant):
    result = []
    host = urlsplit(company["url"]).hostname
    for item in items:
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
        follow_redirects=True,
        headers={"User-Agent": "RapidJobSearch/0.1 (personal career search)"},
    )
    try:
        try:
            items = _load(company, client, report)
        except SourceProblem as error:
            report.status, report.reason = error.status, str(error)
            return report
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            report.status, report.reason = (
                "falhou",
                f"Falha de leitura da fonte: {type(error).__name__}: {error}",
            )
            return report
        seen = set()
        for item in items:
            if time.monotonic() - started > 180 or report.examined >= max_jobs:
                report.status, report.reason = "parcial", "Limite de tempo ou quantidade atingido."
                break
            if item.identity in seen:
                continue
            if not item.title.strip() or urlsplit(item.url).scheme not in {"http", "https"}:
                report.status, report.reason = "parcial", "Anúncio sem título ou link válido."
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
        return report
    finally:
        if owned:
            client.close()
