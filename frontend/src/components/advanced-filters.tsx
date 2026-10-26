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

  const applied = [
    { key: "q" as const, label: "Busca", value: filters.q.trim() },
    { key: "company_id" as const, label: "Empresa", value: filters.company_id ? companies.find((item) => item.id === filters.company_id)?.nome ?? "Selecionada" : "" },
    { key: "role_id" as const, label: "Cargo", value: filters.role_id ? roles.find((item) => item.id === filters.role_id)?.nome ?? "Selecionado" : "" },
    { key: "level_id" as const, label: "Nível", value: filters.level_id ? levels.find((item) => item.id === filters.level_id)?.nome ?? "Selecionado" : "" },
  ].filter((item) => item.value);

  return <div className="advanced-filters-body">
    <div className="advanced-filters-grid">
      <div className="field filters-name-field"><label htmlFor="job-name-search">Busca por nome</label><div className="input-with-icon"><Icon name="search" /><input id="job-name-search" type="search" placeholder="Qual oportunidade você está procurando?" value={filters.q} maxLength={200} onChange={(event) => update("q", event.target.value)} /></div><p className="filters-field-hint">Busque pelo título da vaga ou nome da empresa.</p></div>
      <SearchableSelect icon="building" label="Empresa" allLabel="Todas as empresas" options={companies} value={filters.company_id} onChange={(value) => update("company_id", value)} loading={loading.companies} disabled={errors.includes("empresas")} />
      <SearchableSelect icon="briefcase" label="Cargo" allLabel="Todos os cargos" options={roles} value={filters.role_id} onChange={(value) => update("role_id", value)} loading={loading.roles} disabled={errors.includes("cargos")} />
      <SearchableSelect icon="sliders" label="Nível" allLabel="Todos os níveis" options={levels} value={filters.level_id} onChange={(value) => update("level_id", value)} loading={loading.levels} disabled={errors.includes("níveis")} />
    </div>
    {!!applied.length && <div className="applied-filters" aria-label="Filtros aplicados">{applied.map((item) => <button className="applied-filter" key={item.key} title={`${item.label}: ${item.value}`} aria-label={`Remover filtro de ${item.label.toLowerCase()}`} onClick={() => update(item.key, "")}><span><strong>{item.label}:</strong> {item.value}</span><Icon name="close" /></button>)}</div>}
    <div className="advanced-filters-footnote"><p><span className="filters-auto-dot" />Filtros aplicados automaticamente<span className="filters-footnote-detail">Cargo e nível consideram o título da vaga.</span></p><button className="filters-clear" onClick={() => onChange({ ...emptyJobFilters })} disabled={!applied.length}><Icon name="close" />Limpar filtros</button></div>
    {!!errors.length && <p className="form-error" role="alert">Não foi possível carregar: {errors.join(", ")}. <button className="text-link" onClick={() => setRetry((current) => current + 1)}>Tentar novamente</button></p>}
  </div>;
}
