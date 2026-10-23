"use client";

import { useEffect, useState } from "react";

type Health = { status: string; services: Record<string, string> };
const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchHealth(signal?: AbortSignal): Promise<Health> {
  const response = await fetch(`${apiUrl}/health/ready`, {
    signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(10000)]) : AbortSignal.timeout(10000),
    cache: "no-store",
  });
  if (response.status !== 200 && response.status !== 503) {
    throw new Error(`Resposta inesperada da API: ${response.status}`);
  }
  return response.json();
}

export default function Home() {
  const [health, setHealth] = useState<Health | null>(null);
  const [checking, setChecking] = useState(true);
  const [unavailable, setUnavailable] = useState(false);

  async function checkHealth(signal?: AbortSignal) {
    try {
      setHealth(await fetchHealth(signal));
      setUnavailable(false);
    } catch (error) {
      if (signal?.aborted) return;
      console.log("Não foi possível verificar a API", error);
      setHealth(null);
      setUnavailable(true);
    } finally {
      if (!signal?.aborted) setChecking(false);
    }
  }

  useEffect(() => {
    const controller = new AbortController();
    fetchHealth(controller.signal)
      .then((data) => { if (!controller.signal.aborted) setHealth(data); })
      .catch((error) => {
        if (!controller.signal.aborted) {
          console.log("Não foi possível verificar a API", error);
          setUnavailable(true);
        }
      })
      .finally(() => { if (!controller.signal.aborted) setChecking(false); });
    return () => controller.abort();
  }, []);

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col px-6 py-12 md:py-20">
      <header className="mb-12 border-b border-slate-200 pb-8">
        <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-emerald-700">Busca Vagas · Desenvolvimento</p>
        <h1 className="text-4xl font-semibold tracking-tight text-slate-950 md:text-5xl">Suas próximas oportunidades, em um só lugar.</h1>
        <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-600">A base da aplicação está preparada. As próximas etapas vão conectar suas empresas e palavras-chave à busca de vagas remotas.</p>
      </header>
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold">Ambiente local</h2>
            <p className="mt-1 text-sm text-slate-500">Verificação real da API e dos serviços.</p>
          </div>
          <button onClick={() => { setChecking(true); void checkHealth(); }} disabled={checking} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50">{checking ? "Verificando…" : "Verificar conexão"}</button>
        </div>
        <div aria-live="polite" aria-busy={checking} className="mt-6 grid gap-3 sm:grid-cols-3">
          {[
            ["API FastAPI", unavailable ? "unavailable" : health ? "ok" : "pending"],
            ["PostgreSQL", health?.services.postgres ?? "pending"],
            ["Redis", health?.services.redis ?? "pending"],
          ].map(([name, status]) => (
            <div key={name} className="rounded-xl bg-slate-50 p-4">
              <p className="text-sm font-medium text-slate-700">{name}</p>
              <p className={`mt-2 text-sm ${status === "ok" ? "text-emerald-700" : "text-slate-500"}`}>{checking ? "Verificando…" : status === "ok" ? "Conectado" : status === "unavailable" ? "Indisponível" : "Aguardando conexão"}</p>
            </div>
          ))}
        </div>
        <a className="mt-5 inline-block text-sm font-medium text-emerald-700 underline underline-offset-4" href={`${apiUrl}/docs`} target="_blank" rel="noreferrer">Abrir documentação da API ↗</a>
      </section>
      <section className="mt-8 grid gap-4 md:grid-cols-3" aria-label="Próximas funcionalidades">
        {[
          ["01", "Empresas", "Cadastro por nome e URL, com importação e exportação em JSON."],
          ["02", "Palavras-chave", "Termos no título das vagas, sempre com filtro de trabalho remoto."],
          ["03", "Pesquisa", "Contagem progressiva e resultados com links, em uma listagem paginada."],
        ].map(([step, title, description]) => (
          <article key={step} className="rounded-xl border border-slate-200 p-5">
            <span className="text-xs font-semibold text-slate-400">{step} · Em breve</span>
            <h2 className="mt-3 font-semibold">{title}</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
