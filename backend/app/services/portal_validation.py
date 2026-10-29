import logging
import time
from dataclasses import asdict
from uuid import uuid4

from redis import Redis
from rq import Queue
from sqlalchemy import delete, update

from app.collectors.portals import collect_company
from app.collectors.support import log_support, support_diagnostic
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.portal_validation import PortalValidation

logger = logging.getLogger(__name__)


def validation_queue():
    return Queue(
        "searches",
        connection=Redis.from_url(
            get_settings().redis_url, socket_connect_timeout=2, socket_timeout=2
        ),
    )


class PortalValidationService:
    def __init__(
        self,
        session_factory=SessionLocal,
        queue_factory=validation_queue,
        collector=collect_company,
    ):
        self.session_factory = session_factory
        self.queue_factory = queue_factory
        self.collector = collector

    def schedule(self, company):
        token = str(uuid4())
        try:
            with self.session_factory() as session:
                record = session.get(PortalValidation, company["id"])
                if not record:
                    record = PortalValidation(company_id=company["id"])
                    session.add(record)
                record.url, record.request_token = company["url"], token
                record.state, record.result, record.requested_at = "pending", None, time.time()
                session.commit()
            self.queue_factory().enqueue(
                "app.services.portal_validation.validate_portal_job",
                company,
                token,
                job_id=f"portal-{token}",
                job_timeout=210,
                result_ttl=60,
            )
            return {
                "validation_state": "pending",
                "company_id": company["id"],
                "url": company["url"],
            }
        except Exception:
            logger.exception("Validação não agendada; cadastro de empresa foi preservado")
            result = support_diagnostic(
                {
                    "company": company["nome"],
                    "url": company["url"],
                    "status": "falhou",
                    "reason_code": "validation_unavailable",
                    "reason": "Validação indisponível no momento; verifique banco, Redis e worker.",
                },
                company["id"],
                token,
            )
            self._store(company, token, result)
            log_support(result)
            return result

    def _store(self, company, token, result):
        try:
            with self.session_factory() as session:
                changed = session.execute(
                    update(PortalValidation)
                    .where(
                        PortalValidation.company_id == company["id"],
                        PortalValidation.request_token == token,
                        PortalValidation.url == company["url"],
                    )
                    .values(state=result["validation_state"], result=result)
                ).rowcount
                session.commit()
                return bool(changed)
        except Exception:
            logger.exception("Não foi possível armazenar a validação da URL")
            return False

    def run(self, company, token):
        with self.session_factory() as session:
            record = session.get(PortalValidation, company["id"])
            if not record or record.request_token != token or record.url != company["url"]:
                return  # Empresa removida ou URL editada após o agendamento.
        try:
            report = self.collector(company, lambda item: None)
            payload = asdict(report)
        except Exception:
            logger.exception("Validação de portal interrompida")
            payload = {
                "company": company["nome"],
                "url": company["url"],
                "status": "falhou",
                "reason_code": "validation_error",
                "reason": "Não foi possível concluir a validação; tente novamente.",
            }
        result = support_diagnostic(payload, company["id"], token)
        if self._store(company, token, result):
            log_support(result)

    def remove(self, company_id):
        try:
            with self.session_factory() as session:
                session.execute(
                    delete(PortalValidation).where(PortalValidation.company_id == company_id)
                )
                session.commit()
        except Exception:
            logger.exception("Não foi possível limpar a validação da empresa removida")


def validate_portal_job(company, token):
    PortalValidationService().run(company, token)


def get_validation_service():
    return PortalValidationService()
