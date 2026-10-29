export type ConfigurationSummary = {
  company_count: number;
  selected_role_count: number;
  active_search_id: string | null;
  search_available?: boolean;
  latest_search_id?: string | null;
};

export type SearchStatus = {
  id: string;
  status: "queued" | "running" | "completed" | "interrupted" | "cancelled";
  found_count: number;
  diagnostics?: SourceValidation[];
  source_validations?: SourceValidation[];
};

export type SourceValidation = {
  id: string; company: string; message: string; status?: string;
  url?: string; resolved_url?: string; platform?: string; checked_at?: string | null;
  label?: string; support_status?: "compatible" | "needs_adaptation" | "access_blocked" | null;
  collection_status?: string; code?: string; validation_state?: string;
};

export type JobsPage = {
  items: { id: string; company: string; title: string; url: string; modality: "remote" | "hybrid" | "onsite" | "unknown"; location?: string }[];
  total: number;
  page: number;
  page_size: number;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function requestApi<T>(path: string, options: RequestInit = {}): Promise<T> {
  const timeout = AbortSignal.timeout(10000);
  const response = await fetch(`${apiUrl}${path}`, {
    ...options,
    cache: "no-store",
    signal: options.signal ? AbortSignal.any([options.signal, timeout]) : timeout,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    const message = typeof detail === "string" ? detail : Array.isArray(detail)
      ? detail.map((item: { loc?: string[]; msg?: string }) => `${item.loc?.at(-1) ?? "Campo"}: ${item.msg ?? "valor inválido"}`).join("; ")
      : `Não foi possível concluir a operação (HTTP ${response.status}).`;
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

// Vagas só devem abrir endereços HTTP(S), mesmo quando fornecidos por um portal.
export function jobLink(url: string): string | null {
  try {
    const parsed = new URL(url);
    return ["http:", "https:"].includes(parsed.protocol) ? parsed.href : null;
  } catch {
    return null;
  }
}
