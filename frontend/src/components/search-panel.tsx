"use client";

import { useEffect, useState } from "react";

import { Icon } from "@/components/icon";
import { jobLink, requestApi, type ConfigurationSummary, type JobsPage, type SearchStatus } from "@/lib/search-api";

export function SearchPanel({ active, companiesRevision, onConfigure }: { active: boolean; companiesRevision: number; onConfigure: () => void }) {
  const [summary, setSummary] = useState<ConfigurationSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [search, setSearch] = useState<SearchStatus | null>(null);
  const [starting, setStarting] = useState(false);
  const [jobs, setJobs] = useState<JobsPage | null>(null);
  const [page, setPage] = useState(1);
  const [loadingJobs, setLoadingJobs] = useState(false);

  const running = search?.status === "queued" || search?.status === "running";
  const completed = search?.status === "completed";
  const configured = !!summary && summary.company_count > 0 && summary.selected_role_count > 0;
  const canSearch = configured && summary?.search_available === true;

  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    requestApi<ConfigurationSummary>("/api/configuration/summary", { signal: controller.signal })
      .then((data) => {
        if (controller.signal.aborted) return;
        setSummary(data);
        if (data.active_search_id) {
          return requestApi<SearchStatus>(`/api/searches/${encodeURIComponent(data.active_search_id)}`, { signal: controller.signal })
            .then((active) => { if (!controller.signal.aborted) setSearch(active); });
        }
      })
      .catch((error) => { if (!controller.signal.aborted) console.log("Configuração de pesquisa ainda indisponível", error); })
      .finally(() => { if (!controller.signal.aborted) setSummaryLoading(false); });
    return () => controller.abort();
  }, [active, companiesRevision]);

  const searchId = search?.id;
  useEffect(() => {
    if (!running || !searchId) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const data = await requestApi<SearchStatus>(`/api/searches/${encodeURIComponent(searchId!)}`, { signal: controller.signal });
        if (controller.signal.aborted) return;
        setSearch(data);
        if (data.status !== "queued" && data.status !== "running") return;
      } catch (error) {
        if (controller.signal.aborted) return;
        console.log("Não foi possível atualizar a pesquisa; nova tentativa será feita", error);
      }
      timer = setTimeout(() => void poll(), 2000);
    }
    timer = setTimeout(() => void poll(), 1000);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [running, searchId]);

  useEffect(() => {
    if (!completed || !searchId) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setLoadingJobs(true);
      requestApi<JobsPage>(`/api/searches/${encodeURIComponent(searchId)}/jobs?page=${page}&page_size=20`, { signal: controller.signal })
        .then((data) => { if (!controller.signal.aborted) setJobs(data); })
        .catch((error) => { if (!controller.signal.aborted) console.log("Não foi possível carregar as vagas", error); })
        .finally(() => { if (!controller.signal.aborted) setLoadingJobs(false); });
    }, 0);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [completed, searchId, page]);

  async function startSearch() {
    if (!canSearch || starting || running) return;
    setStarting(true);
    try {
      const data = await requestApi<SearchStatus>("/api/searches", { method: "POST" });
      setJobs(null);
      setPage(1);
      setSearch(data);
    } catch (error) {
      console.log("Não foi possível iniciar a pesquisa", error);
    } finally {
      setStarting(false);
    }
  }

  return (
    <>
      <section className="search-summary" aria-label="Resumo da configuração" aria-busy={summaryLoading}>
        <article className="card summary-card"><span className="section-icon"><Icon name="building" /></span><div><p>Empresas cadastradas</p><strong>{summary?.company_count ?? "—"}</strong><span>Portais para consultar</span></div><button className="text-link" onClick={onConfigure}>Gerenciar</button></article>
        <article className="card summary-card"><span className="section-icon"><Icon name="briefcase" /></span><div><p>Cargos selecionados</p><strong>{summary?.selected_role_count ?? "—"}</strong><span>Seu próximo passo profissional</span></div><button className="text-link" onClick={onConfigure}>Configurar</button></article>
      </section>

      <section className="search-bar" aria-labelledby="search-title" aria-busy={starting || running}>
        <div><h2 id="search-title">Encontre suas próximas oportunidades</h2><p>Consulte as empresas cadastradas e acompanhe as vagas remotas dos cargos selecionados.</p>
          <span className="implementation-note" id="search-prerequisites">{!summary ? "O cadastro e a pesquisa serão conectados nas próximas etapas. Os totais aparecerão assim que os dados estiverem disponíveis." : !configured ? "Cadastre pelo menos uma empresa e selecione um cargo na aba Empresas e cargos." : summary.search_available ? "Tudo pronto. Você já pode realizar sua pesquisa." : "Empresas e cargos configurados. A busca será liberada após a integração dos portais."}</span>
        </div>
        <button className="button button-primary search-button" disabled={!canSearch || starting || running} aria-describedby="search-prerequisites" onClick={() => void startSearch()}>{starting || running ? <span className="spinner" aria-hidden="true" /> : <Icon name="search" />}{starting ? "Iniciando pesquisa…" : running ? "Buscando vagas…" : "Buscar vagas"}</button>
      </section>

      <div className="search-live-status" role="status" aria-live="polite" aria-atomic="true">
        {starting && <p className="progress-message"><span className="spinner" aria-hidden="true" /> Preparando sua pesquisa…</p>}
        {!starting && running && <p className="progress-message"><span className="spinner" aria-hidden="true" /><span>Pesquisa em andamento. <strong>{search.found_count} {search.found_count === 1 ? "vaga encontrada" : "vagas encontradas"}</strong> até agora.</span></p>}
        {completed && <p className="completion-message"><Icon name="check" /><span>Pesquisa finalizada: <strong>{search.found_count} {search.found_count === 1 ? "vaga encontrada" : "vagas encontradas"}</strong>.</span></p>}
        {(search?.status === "interrupted" || search?.status === "cancelled") && <p className="implementation-note">Pesquisa encerrada antes da conclusão. Você pode iniciar uma nova busca.</p>}
      </div>

      <section id="resultados" className="card results-card" aria-labelledby="results-title" aria-busy={loadingJobs}>
        <div className="results-heading"><div><span className="eyebrow">SUAS OPORTUNIDADES</span><h2 id="results-title">Vagas encontradas</h2></div><span className="badge badge-remote"><Icon name="globe" /> Remotas</span></div>
        <div className="table-scroll"><table className="jobs-table"><caption className="sr-only">Vagas por empresa e nome, com link para o anúncio.</caption><thead><tr><th scope="col">Empresa</th><th scope="col">Nome da vaga</th></tr></thead><tbody>
          {jobs?.items.length ? jobs.items.map((job) => { const href = jobLink(job.url); return <tr key={job.id}><td className="job-cell">{job.company}</td><td className="job-cell">{href ? <a className="text-link" href={href} target="_blank" rel="noreferrer">{job.title} ↗</a> : job.title}</td></tr>; }) : <tr><td colSpan={2}><div className="empty-state"><span className="empty-icon">{loadingJobs || running ? <span className="spinner" aria-hidden="true" /> : <Icon name="briefcase" />}</span><h3>{loadingJobs ? "Carregando suas oportunidades…" : running ? "Estamos procurando por você" : completed ? search.found_count === 0 ? "Nenhuma vaga encontrada nesta pesquisa" : "Suas oportunidades estão sendo carregadas" : "Sua lista de oportunidades começa aqui"}</h3><p>{running ? "Acompanhe a contagem acima. Ao finalizar, suas vagas serão listadas aqui." : completed && search.found_count === 0 ? "Ajuste suas empresas e cargos e tente uma nova busca." : "Suas vagas aparecerão nesta tabela, com links diretos para os anúncios."}</p>{!search && <span className="empty-hint">Nenhuma pesquisa realizada</span>}</div></td></tr>}
        </tbody></table></div>
        {jobs && jobs.total > jobs.page_size && <nav className="pagination" aria-label="Paginação de vagas"><button className="button button-secondary button-small" disabled={page <= 1 || loadingJobs} onClick={() => setPage(page - 1)}>Anterior</button><span>Página {jobs.page} de {Math.ceil(jobs.total / jobs.page_size)}</span><button className="button button-secondary button-small" disabled={page >= Math.ceil(jobs.total / jobs.page_size) || loadingJobs} onClick={() => setPage(page + 1)}>Próxima</button></nav>}
      </section>
      <p className="search-footnote">Quer ajustar onde e o que procurar? <button className="text-link" onClick={onConfigure}>Abra Empresas e cargos</button>.</p>
    </>
  );
}
