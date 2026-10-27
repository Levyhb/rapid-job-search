"use client";

import { useEffect, useId, useRef, useState } from "react";

import { Icon } from "@/components/icon";

export type SelectOption = { id: string; nome: string };

const normalize = (text: string) => text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

export function SearchableSelect({ label, options, value, onChange, loading = false, disabled = false, allLabel }: {
  label: string; options: SelectOption[]; value: string; onChange: (value: string) => void;
  loading?: boolean; disabled?: boolean; allLabel: string;
}) {
  const id = useId();
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [highlighted, setHighlighted] = useState(0);
  const filtered = [{ id: "", nome: allLabel }, ...options].filter((item) => normalize(item.nome).includes(normalize(query.trim())));

  useEffect(() => {
    if (!open) return;
    input.current?.focus();
    function outside(event: PointerEvent) {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("pointerdown", outside);
    return () => document.removeEventListener("pointerdown", outside);
  }, [open]);

  useEffect(() => {
    if (open) document.getElementById(`${id}-option-${highlighted}`)?.scrollIntoView({ block: "nearest" });
  }, [highlighted, open, id]);

  function choose(next: string) {
    onChange(next); setOpen(false); trigger.current?.focus();
  }

  return <div className="field searchable-select" ref={root} onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setOpen(false); }}>
    <label id={`${id}-label`}>{label}</label>
    <button type="button" className={`select-trigger${value ? " has-selection" : ""}`} ref={trigger} aria-labelledby={`${id}-label ${id}-value`} aria-haspopup="listbox" aria-expanded={open} aria-controls={`${id}-list`} aria-busy={loading} disabled={loading || disabled} onClick={() => { setQuery(""); setHighlighted(0); setOpen(!open); }}>
      <span id={`${id}-value`}>{loading ? "Carregando…" : options.find((item) => item.id === value)?.nome ?? allLabel}</span>
      {loading ? <span className="spinner" aria-hidden="true" /> : <Icon name="chevronDown" />}
    </button>
    {open && <div className="select-dropdown">
      <div className="select-search"><Icon name="search" /><input ref={input} role="combobox" aria-label={`Buscar ${label.toLowerCase()}`} aria-expanded="true" aria-controls={`${id}-list`} aria-autocomplete="list" aria-activedescendant={filtered[highlighted] ? `${id}-option-${highlighted}` : undefined} placeholder="Digite para buscar…" value={query} onChange={(event) => { setQuery(event.target.value); setHighlighted(0); }} onKeyDown={(event) => {
        if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); setOpen(false); trigger.current?.focus(); }
        if (event.key === "ArrowDown" || event.key === "ArrowUp") { event.preventDefault(); setHighlighted((current) => Math.max(0, Math.min(filtered.length - 1, current + (event.key === "ArrowDown" ? 1 : -1)))); }
        if (event.key === "Enter") { event.preventDefault(); if (filtered[highlighted]) choose(filtered[highlighted].id); }
      }} /></div>
      <ul id={`${id}-list`} role="listbox" aria-labelledby={`${id}-label`}>{filtered.map((item, index) => <li key={item.id} id={`${id}-option-${index}`} role="option" aria-selected={item.id === value} className={highlighted === index ? "select-highlighted" : ""} onPointerMove={() => setHighlighted(index)} onMouseDown={(event) => event.preventDefault()} onClick={() => choose(item.id)}>{item.nome}{item.id === value && <Icon name="check" />}</li>)}</ul>
      {!filtered.length && <p className="select-empty">Nenhuma opção encontrada.</p>}
    </div>}
  </div>;
}
