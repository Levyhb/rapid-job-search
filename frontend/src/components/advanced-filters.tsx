"use client";

import { useEffect, useState } from "react";

import { Icon } from "@/components/icon";
import { SearchableSelect, type SelectOption } from "@/components/searchable-select";
import { requestApi } from "@/lib/search-api";

export type JobFilters = { q: string; company_id: string; role_id: string; level_id: string };
export const emptyJobFilters: JobFilters = { q: "", company_id: "", role_id: "", level_id: "" };

export function AdvancedFilters({ filters, onChange, revision }: { filters: JobFilters; onChange: (filters: JobFilters) => void; revision: number }) {
  const [companies, setCompanies] = useState<SelectOption[]>([]);
  const [roles, setRoles] = useState<SelectOption[]>([]);
  const [levels, setLevels] = useState<SelectOption[]>([]);
  const [loading, setLoading] = useState({ companies: true, roles: true, levels: true });
  const [errors, setErrors] = useState<string[]>([]);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setLoading({ companies: true, roles: true, levels: true }); setErrors([]);
      const sources = [
        { key: "companies" as const, path: "/api/companies", set: setCompanies, label: "empresas" },
        { key: "roles" as const, path: "/api/roles", set: setRoles, label: "cargos" },
        { key: "levels" as const, path: "/api/searches/levels", set: setLevels, label: "níveis" },
      ];
      for (const source of sources) {
        requestApi<SelectOption[]>(source.path, { signal: controller.signal })
          .then((data) => { if (!controller.signal.aborted) source.set(data); })
          .catch(() => { if (!controller.signal.aborted) { source.set([]); setErrors((current) => [...current, source.label]); } })
          .finally(() => { if (!controller.signal.aborted) setLoading((current) => ({ ...current, [source.key]: false })); });
      }
    }, 0);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [revision, retry]);

  function update(key: keyof JobFilters, value: string) { onChange({ ...filters, [key]: value }); }

  return <div className="advanced-filters-body">
    <div className="advanced-filters-grid">
      <div className="field"><label htmlFor="job-name-search">Busca por nome</label><div className="input-with-icon"><Icon name="search" /><input id="job-name-search" type="search" placeholder="Buscar título da vaga ou empresa" value={filters.q} maxLength={200} onChange={(event) => update("q", event.target.value)} /></div></div>
      <SearchableSelect label="Empresa" allLabel="Todas as empresas" options={companies} value={filters.company_id} onChange={(value) => update("company_id", value)} loading={loading.companies} disabled={errors.includes("empresas")} />
      <SearchableSelect label="Cargo" allLabel="Todos os cargos" options={roles} value={filters.role_id} onChange={(value) => update("role_id", value)} loading={loading.roles} disabled={errors.includes("cargos")} />
      <SearchableSelect label="Nível" allLabel="Todos os níveis" options={levels} value={filters.level_id} onChange={(value) => update("level_id", value)} loading={loading.levels} disabled={errors.includes("níveis")} />
    </div>
    <div className="advanced-filters-footnote"><p>Cargo e nível consideram o título da vaga e suas variações cadastradas.</p><button className="text-link" onClick={() => onChange({ ...emptyJobFilters })} disabled={!Object.values(filters).some(Boolean)}>Limpar filtros</button></div>
    {!!errors.length && <p className="form-error" role="alert">Não foi possível carregar: {errors.join(", ")}. <button className="text-link" onClick={() => setRetry((current) => current + 1)}>Tentar novamente</button></p>}
  </div>;
}
