import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from redis import Redis
from rq import Queue, Worker
from rq.job import Job
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.companies import get_catalog
from app.collectors.support import support_diagnostic
from app.core.config import get_settings
from app.core.database import get_session
from app.models.role import Role
from app.models.search import SearchJob, SearchRun
from app.services.company_catalog import CompanyCatalog

router = APIRouter(prefix="/api/searches", tags=["Pesquisas"])
logger = logging.getLogger(__name__)


def get_queue():
    return Queue(
        "searches",
        connection=Redis.from_url(
            get_settings().redis_url, socket_connect_timeout=3, socket_timeout=3
        ),
    )


def recover_run(run, session, queue):
    if run.status not in {"queued", "running"} or time.time() - run.updated_at < 30:
        return
    try:
        job = Job.fetch(run.id, connection=queue.connection)
        status = job.get_status()
        interrupted = status in {"failed", "stopped", "canceled", "finished"}
    except Exception:
        # Falha de Redis não prova que o worker morreu; usar o heartbeat persistido.
        interrupted = time.time() - run.updated_at > 600
    if interrupted:
        run.status, run.active_key = "interrupted", None
        session.commit()


def run_payload(run, session):
    validations = [
        report.get("validation")
        or {
            **support_diagnostic(report, event_id=f"{run.id}:{index}"),
            "checked_at": None,  # Execuções antigas não registravam a data por fonte.
        }
        for index, report in enumerate(run.reports)
        if report["status"] != "consultando"
    ]
    return {
        "id": run.id,
        "status": run.status,
        "found_count": session.scalar(
            select(func.count()).select_from(SearchJob).where(SearchJob.run_id == run.id)
        ),
        "source_validations": validations,
        "diagnostics": [
            {**item, "status": item["collection_status"]}
            for item in validations
            if item["collection_status"] != "concluida"
        ],
    }


@router.post("", status_code=202)
def start_search(
    session: Session = Depends(get_session),
    catalog: CompanyCatalog = Depends(get_catalog),
    queue=Depends(get_queue),
):
    active = session.scalar(select(SearchRun).where(SearchRun.active_key == "active"))
    if active:
        recover_run(active, session, queue)
        if active.active_key:
            raise HTTPException(409, "Já existe uma pesquisa em andamento.")
    companies = catalog.list()
    roles = session.scalars(select(Role).where(Role.selecionado.is_(True))).all()
    if not companies or not roles:
        raise HTTPException(422, "Cadastre uma empresa e selecione pelo menos um cargo.")
    try:
        if not queue.connection.ping() or not Worker.all(queue=queue):
            raise HTTPException(503, "Inicie o worker de pesquisa antes de buscar.")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, "Fila indisponível. Inicie Redis e o worker.") from None
    run = SearchRun(
        active_key="active",
        configuration={
            "companies": [company.model_dump() for company in companies],
            "roles": [
                {"id": role.id, "nome": role.nome, "variacoes": role.variacoes} for role in roles
            ],
        },
    )
    session.add(run)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Já existe uma pesquisa em andamento.") from None
    try:
        queue.enqueue(
            "app.workers.searches.run_search",
            run.id,
            job_id=run.id,
            job_timeout=min(7200, len(companies) * 180 + 120),
            result_ttl=86400,
        )
    except Exception:
        run.status, run.active_key = "interrupted", None
        session.commit()
        raise HTTPException(503, "Não foi possível iniciar a tarefa. Tente novamente.") from None
    return run_payload(run, session)


@router.get("/{run_id}")
def search_status(run_id: str, session: Session = Depends(get_session), queue=Depends(get_queue)):
    run = session.get(SearchRun, run_id)
    if not run:
        raise HTTPException(404, "Pesquisa não encontrada.")
    recover_run(run, session, queue)
    return run_payload(run, session)


@router.get("/{run_id}/diagnostics")
def diagnostics(run_id: str, session: Session = Depends(get_session)):
    run = session.get(SearchRun, run_id)
    if not run:
        raise HTTPException(404, "Pesquisa não encontrada.")
    return {"items": run_payload(run, session)["diagnostics"]}


@router.get("/{run_id}/jobs")
def search_jobs(
    run_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    if not session.get(SearchRun, run_id):
        raise HTTPException(404, "Pesquisa não encontrada.")
    total = session.scalar(
        select(func.count()).select_from(SearchJob).where(SearchJob.run_id == run_id)
    )
    jobs = session.scalars(
        select(SearchJob)
        .where(SearchJob.run_id == run_id)
        .order_by(SearchJob.created_at.desc(), SearchJob.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [
            {
                "id": job.id,
                "company": job.company,
                "title": job.title,
                "url": job.url,
                "modality": job.modality,
                "modality_original": job.modality_original,
                "location": job.location,
            }
            for job in jobs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
