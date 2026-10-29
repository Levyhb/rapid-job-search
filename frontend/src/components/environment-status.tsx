"use client";

import { useEffect, useState } from "react";

type Health = { status: string; services: Record<string, string> };
const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchHealth(signal?: AbortSignal): Promise<Health> {
  const timeout = AbortSignal.timeout(10000);
  const response = await fetch(`${apiUrl}/health/ready`, {
    signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
    cache: "no-store",
  });
  if (response.status !== 200 && response.status !== 503) {
    throw new Error(`Resposta inesperada da API: ${response.status}`);
  }
  return response.json();
}

export function EnvironmentStatus() {
  const [health, setHealth] = useState<Health | null>(null);
  const [checking, setChecking] = useState(true);
  const [unavailable, setUnavailable] = useState(false);

  async function checkHealth() {
    setChecking(true);
    try {
      setHealth(await fetchHealth());
      setUnavailable(false);
    } catch (error) {
      console.log("Não foi possível verificar a API", error);
      setHealth(null);
      setUnavailable(true);
    } finally {
      setChecking(false);
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
    <details className="environment">
      <summary>Ambiente de desenvolvimento</summary>
      <div className="environment-content">
        <div aria-live="polite" aria-busy={checking} className="service-grid">
          {[
            ["API FastAPI", unavailable ? "unavailable" : health ? "ok" : "pending"],
            ["PostgreSQL", health?.services.postgres ?? "pending"],
            ["Redis", health?.services.redis ?? "pending"],
          ].map(([name, status]) => (
            <div key={name} className="service-item">
              <span>{name}</span>
              <strong className={status === "ok" ? "service-ok" : ""}>
                {checking ? "Verificando…" : status === "ok" ? "Conectado" : status === "unavailable" ? "Indisponível" : "Aguardando conexão"}
              </strong>
            </div>
          ))}
        </div>
        <div className="environment-actions">
          <button className="button button-secondary button-small" onClick={() => void checkHealth()} disabled={checking}>
            {checking ? "Verificando…" : "Verificar conexão"}
          </button>
          <a className="text-link" href={`${apiUrl}/docs`} target="_blank" rel="noreferrer">Documentação da API ↗</a>
        </div>
      </div>
    </details>
  );
}
