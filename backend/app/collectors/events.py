"""Coleta concorrente sem compartilhar navegador nem sessão de banco entre threads."""

import logging
from concurrent.futures import ThreadPoolExecutor
from queue import Empty, Full, Queue
from threading import Event

from app.collectors.browser import CollectorSession
from app.collectors.portals import CollectionReport


def collect_events(companies, roles, session_factory=CollectorSession):
    events = Queue(maxsize=100)
    stopped = Event()
    workers = min(2, len(companies))

    def emit(kind, payload):
        while not stopped.is_set():
            try:
                events.put((kind, payload), timeout=0.2)
                return
            except Full:
                continue

    def collect_group(group):
        try:
            with session_factory(roles=roles) as collector:
                for company in group:
                    if stopped.is_set():
                        break
                    try:
                        report = collector.collect(
                            company,
                            lambda item: emit("job", item),
                            lambda report: emit("progress", report),
                        )
                    except Exception:
                        report = CollectionReport(
                            company["nome"],
                            company["url"],
                            status="falhou",
                            reason="Coletor interrompido; consulte os logs do worker.",
                            reason_code="collector_error",
                        )
                        logging.getLogger(__name__).exception("Falha ao coletar %s", company["url"])
                    emit("report", (company, report))
        finally:
            emit("done", None)

    with ThreadPoolExecutor(max_workers=workers or 1) as executor:
        tasks = [executor.submit(collect_group, companies[i::workers]) for i in range(workers)]
        completed = 0
        try:
            while completed < workers:
                try:
                    kind, payload = events.get(timeout=0.5)
                except Empty:
                    for task in tasks:
                        if task.done():
                            task.result()
                    continue
                if kind == "done":
                    completed += 1
                else:
                    yield kind, payload
            for task in tasks:
                task.result()
        finally:
            stopped.set()
