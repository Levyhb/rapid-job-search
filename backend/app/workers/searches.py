import logging
import time
from dataclasses import asdict

from sqlalchemy import select

from app.collectors.portals import collect_company
from app.core.database import SessionLocal
from app.filters.role_matching import match_title
from app.models.search import SearchJob, SearchRun

logger = logging.getLogger(__name__)


def run_search(run_id, session_factory=SessionLocal, collector=collect_company):
    with session_factory() as session:
        run = session.get(SearchRun, run_id)
        if not run or run.status != "queued":
            return
        run.status = "running"
        run.updated_at = time.time()
        session.commit()
        roles = run.configuration["roles"]
        seen = set(session.scalars(select(SearchJob.identity).where(SearchJob.run_id == run_id)))
        try:
            for company in run.configuration["companies"]:

                def save_job(item):
                    if item.identity in seen or item.modality != "remote":
                        return
                    matches = [
                        {"id": role["id"], "nome": role["nome"], "termos": terms}
                        for role in roles
                        if (terms := match_title(item.title, role["nome"], role["variacoes"]))
                    ]
                    if not matches:
                        return
                    session.add(
                        SearchJob(
                            run_id=run_id,
                            identity=item.identity,
                            company=item.company,
                            title=item.title,
                            url=item.url,
                            modality=item.modality,
                            modality_original=item.modality_original,
                            location=item.location,
                            matches=matches,
                        )
                    )
                    run.updated_at = time.time()
                    session.commit()
                    seen.add(item.identity)

                def progress(report):
                    run.reports = [
                        entry for entry in run.reports if entry["url"] != report["url"]
                    ] + [report]
                    run.updated_at = time.time()
                    session.commit()

                report = collector(company, save_job, progress)
                progress(asdict(report))
                if report.status != "concluida":
                    logger.warning(
                        "Busca %s | %s | %s | %s",
                        run_id,
                        company["nome"],
                        company["url"],
                        report.reason,
                    )
            run.status, run.active_key = "completed", None
            run.updated_at = time.time()
            session.commit()
        except BaseException:
            session.rollback()
            run = session.get(SearchRun, run_id)
            if run:
                run.status, run.active_key = "interrupted", None
                run.updated_at = time.time()
                session.commit()
            logger.exception("Execução %s interrompida", run_id)
            raise
