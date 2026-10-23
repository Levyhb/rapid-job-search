export type ConfigurationSummary = {
  company_count: number;
  selected_role_count: number;
  active_search_id: string | null;
};

export type SearchStatus = {
  id: string;
  status: "queued" | "running" | "completed" | "interrupted" | "cancelled";
  found_count: number;
};

export type JobsPage = {
  items: { id: string; company: string; title: string; url: string }[];
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
  if (!response.ok) throw new Error(`${options.method ?? "GET"} ${path}: HTTP ${response.status}`);
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
