import html
import json
import logging
import re
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlsplit

logger = logging.getLogger(__name__)


def identify_platform(url, page_html=""):
    host = (urlsplit(url).hostname or "").lower()
    if host.endswith(".inhire.app"):
        return "inhire", host.split(".")[0]
    if host.endswith(".gupy.io"):
        return "gupy", host.split(".")[0]
    if host in {"boards.greenhouse.io", "job-boards.greenhouse.io"}:
        return "greenhouse", urlsplit(url).path.strip("/").split("/")[0]
    embeds = re.findall(
        r'https://boards\.greenhouse\.io/embed/job_board/js\?([^"<>\s]+)', page_html
    )
    tokens = {parse_qs(html.unescape(value)).get("for", [""])[0] for value in embeds}
    tokens.discard("")
    if tokens:
        return "greenhouse", next(iter(tokens)) if len(tokens) == 1 else None
    return "unknown", None


def support_diagnostic(report, company_id=None, event_id=None):
    status = report["status"]
    code = report.get("reason_code", "")
    if status == "concluida":
        support, label = "compatible", "Compatível"
    elif status == "bloqueada":
        support, label = "access_blocked", "Acesso bloqueado"
    elif status in {"nao_suportada", "parcial"} or code == "parse_error":
        support, label = "needs_adaptation", "Precisa de adaptação"
    else:
        support, label = None, "Validação inconclusiva"
    return {
        "id": event_id,
        "company_id": company_id,
        "company": report["company"],
        "url": report["url"],
        "resolved_url": report.get("resolved_url") or report["url"],
        "platform": report.get("source") or "unknown",
        "support_status": support,
        "label": label,
        "validation_state": "completed" if support else "inconclusive",
        "collection_status": status,
        "code": code or status,
        "message": report.get("reason")
        or (
            f"Listagem lida completamente: {report.get('examined', 0)} anúncios examinados."
            if status == "concluida"
            else "Não foi possível concluir a validação desta fonte."
        ),
        "checked_at": datetime.now(UTC).isoformat(),
        "coverage": {key: report.get(key) for key in ("examined", "expected", "batches")},
    }


def log_support(result):
    log = logger.info if result["support_status"] == "compatible" else logger.warning
    log("[%s] %s", result["label"], json.dumps(result, ensure_ascii=False))
