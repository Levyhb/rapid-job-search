"use client";

import { useEffect, useState, type FormEvent } from "react";

import { Icon } from "@/components/icon";
import { Modal } from "@/components/modal";
import { requestApi } from "@/lib/search-api";

type Role = { id: string; nome: string; variacoes: string[]; selecionado: boolean };
type RoleDialog = { kind: "add" } | { kind: "edit" | "remove"; role: Role };
type Preview = { corresponde: boolean; cargos: { id: string; nome: string; termos: string[] }[] };
const errorMessage = (error: unknown) => error instanceof Error ? error.message : "Não foi possível concluir a operação.";

export function RolesManager({ onChanged }: { onChanged: () => void }) {
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [filter, setFilter] = useState("");
  const [dialog, setDialog] = useState<RoleDialog | null>(null);
  const [name, setName] = useState("");
  const [variations, setVariations] = useState("");
  const [selected, setSelected] = useState(true);
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [toast, setToast] = useState<{ message: string } | null>(null);
  const [title, setTitle] = useState("");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [testing, setTesting] = useState(false);
  const [previewError, setPreviewError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    requestApi<Role[]>("/api/roles", { signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setRoles(data); })
      .catch((failure) => { if (!controller.signal.aborted) setLoadError(errorMessage(failure)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 4500);
    return () => clearTimeout(timer);
  }, [toast]);

  async function reload() {
    setLoading(true);
    try { setRoles(await requestApi<Role[]>("/api/roles")); setLoadError(""); }
    catch (failure) { setLoadError(errorMessage(failure)); }
    finally { setLoading(false); }
  }

  function open(next: RoleDialog) {
    setError("");
    setName(next.kind === "edit" ? next.role.nome : "");
    setVariations(next.kind === "edit" ? next.role.variacoes.join("\n") : "");
    setSelected(next.kind === "edit" ? next.role.selecionado : true);
    setDialog(next);
  }

  function confirmed(message: string) {
    setDialog(null);
    setPreview(null);
    setToast({ message });
    onChanged();
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!dialog || dialog.kind === "remove" || busy) return;
    setBusy(true); setError("");
    try {
      const editing = dialog.kind === "edit";
      const saved = await requestApi<Role>(editing ? `/api/roles/${dialog.role.id}` : "/api/roles", {
        method: editing ? "PATCH" : "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nome: name.trim(), variacoes: variations.split(/[\n,]+/).map((value) => value.trim()).filter(Boolean), selecionado: selected }),
      });
      setRoles((current) => (editing ? current.map((role) => role.id === saved.id ? saved : role) : [...current, saved]).sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR")));
      confirmed(editing ? "Cargo atualizado com sucesso." : "Cargo cadastrado com sucesso.");
    } catch (failure) { setError(errorMessage(failure)); }
    finally { setBusy(false); }
  }

  async function remove() {
    if (dialog?.kind !== "remove" || busy) return;
    setBusy(true); setError("");
    try {
      await requestApi(`/api/roles/${dialog.role.id}`, { method: "DELETE" });
      setRoles((current) => current.filter((role) => role.id !== dialog.role.id));
      confirmed("Cargo removido com sucesso.");
    } catch (failure) { setError(errorMessage(failure)); }
    finally { setBusy(false); }
  }

  async function select(role: Role) {
    if (pending) return;
    setPending(role.id);
    setRoles((current) => current.map((item) => item.id === role.id ? { ...item, selecionado: !role.selecionado } : item));
    try {
      const saved = await requestApi<Role>(`/api/roles/${role.id}/selection`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ selecionado: !role.selecionado }) });
      setRoles((current) => current.map((item) => item.id === saved.id ? saved : item));
      setLoadError(""); setPreview(null); onChanged();
      setToast({ message: saved.selecionado ? "Cargo selecionado para a busca." : "Cargo retirado da seleção." });
    } catch (failure) {
      setRoles((current) => current.map((item) => item.id === role.id ? role : item));
      setLoadError(errorMessage(failure));
    }
    finally { setPending(null); }
  }

  async function testTitle(event: FormEvent) {
    event.preventDefault();
    setTesting(true); setPreviewError(""); setPreview(null);
    try { setPreview(await requestApi<Preview>("/api/roles/preview", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ titulo: title }) })); }
    catch (failure) { setPreviewError(errorMessage(failure)); }
    finally { setTesting(false); }
  }

  const normalize = (value: string) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR");
  const filtered = roles.filter((role) => normalize([role.nome, ...role.variacoes].join(" ")).includes(normalize(filter.trim())));

  return (
    <section id="cargos" className="card roles-card" aria-labelledby="roles-title">
      <div className="card-heading"><span className="section-icon"><Icon name="briefcase" /></span><div><h3 id="roles-title">Cargos de interesse</h3><p>Escolha os cargos e suas variações.</p></div><button className="button button-primary button-small add-role" disabled={loading || !!loadError} onClick={() => open({ kind: "add" })}><Icon name="plus" /> Adicionar cargo</button></div>
      <div className="field company-filter"><label htmlFor="role-search">Buscar cargo</label><div className="input-with-icon"><Icon name="search" /><input id="role-search" type="search" value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="Filtrar por cargo ou variação" /></div></div>
      <div className="company-list-caption" aria-live="polite">{loading ? "Carregando cargos…" : `${roles.length} cadastrados · ${roles.filter((role) => role.selecionado).length} selecionados${filter.trim() ? ` · ${filtered.length} no filtro` : ""}`}</div>
      {loadError && <div className="form-error" role="alert">{loadError} <button className="text-link" onClick={() => void reload()}>Tentar novamente</button></div>}
      <div className="company-list roles-list" role="region" aria-label="Cargos cadastrados" tabIndex={0} aria-busy={loading} onScroll={(event) => event.currentTarget.querySelectorAll<HTMLElement>("[popover]:popover-open").forEach((element) => element.hidePopover())}>
        {!loading && !loadError && !filtered.length && <div className="companies-empty"><Icon name="briefcase" /><h4>{roles.length ? "Nenhum cargo corresponde ao filtro" : "Quais cargos você quer encontrar?"}</h4><p>{roles.length ? "Tente outro cargo ou variação." : "Cadastre, por exemplo, Desenvolvedor e adicione Dev e Developer como variações."}</p></div>}
        <ul className="company-rows">{filtered.map((role) => <li key={role.id} className="role-row"><input className="role-checkbox" type="checkbox" checked={role.selecionado} disabled={!!pending} onChange={() => void select(role)} aria-label={`Incluir ${role.nome} na busca`} /><div className="role-info"><strong title={role.nome}>{role.nome}</strong><span title={role.variacoes.join(", ")}>{role.variacoes.length ? role.variacoes.join(" · ") : "Sem variações adicionais"}</span></div>
          <button className="icon-button company-actions-trigger" popoverTarget={`role-actions-${role.id}`} aria-label={`Ações do cargo ${role.nome}`} onClick={(event) => { const rect = event.currentTarget.getBoundingClientRect(); const element = document.getElementById(`role-actions-${role.id}`); element?.style.setProperty("--menu-left", `${Math.max(8, rect.right - 150)}px`); element?.style.setProperty("--menu-top", `${Math.min(innerHeight - 110, rect.bottom + 5)}px`); }}><Icon name="more" /></button>
          <div popover="auto" id={`role-actions-${role.id}`} className="company-actions-menu" role="menu" aria-label={`Opções do cargo ${role.nome}`} onToggle={(event) => { if (event.currentTarget.matches(":popover-open")) event.currentTarget.querySelector<HTMLButtonElement>("button")?.focus(); }} onKeyDown={(event) => { if (["ArrowUp", "ArrowDown"].includes(event.key)) { event.preventDefault(); const buttons = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>("button")); const index = buttons.indexOf(document.activeElement as HTMLButtonElement); buttons[(index + (event.key === "ArrowDown" ? 1 : -1) + buttons.length) % buttons.length]?.focus(); } }}><button role="menuitem" onClick={() => { document.getElementById(`role-actions-${role.id}`)?.hidePopover(); open({ kind: "edit", role }); }}><Icon name="edit" /> Editar</button><button role="menuitem" className="danger-text" onClick={() => { document.getElementById(`role-actions-${role.id}`)?.hidePopover(); open({ kind: "remove", role }); }}><Icon name="trash" /> Remover</button></div>
        </li>)}</ul>
      </div>
      <p className="implementation-note">Basta um termo corresponder ao título. Desenvolvedor e Desenvolvedora são reconhecidos; use variações amplas, como Backend, para alcançar mais vagas.</p>
      <details className="role-preview"><summary>Testar título de vaga</summary><form onSubmit={testTitle}><div className="field"><label htmlFor="title-preview">Título para testar</label><input id="title-preview" required maxLength={500} value={title} onChange={(event) => { setTitle(event.target.value); setPreview(null); }} placeholder="Ex.: Dev Backend Júnior" disabled={testing} /></div><button className="button button-secondary button-small" disabled={testing || !roles.some((role) => role.selecionado)}>{testing ? "Testando…" : "Testar título"}</button></form><div className="preview-result" role="status" aria-live="polite">{preview && <p>{preview.corresponde ? `Corresponde a: ${preview.cargos.map((role) => `${role.nome} (${role.termos.join(", ")})`).join("; ")}.` : "Nenhum cargo selecionado corresponde a esse título."}</p>}</div>{previewError && <p className="form-error" role="alert">{previewError}</p>}<p className="implementation-note">Esta prévia testa o título com as mesmas regras da pesquisa. A modalidade remota é verificada separadamente.</p></details>
      <div className="remote-rule"><span className="remote-rule-icon"><Icon name="check" /></span><div><strong>Somente trabalho remoto</strong><p>O cargo não define a modalidade. Vagas presenciais e híbridas ficam fora da busca.</p></div></div>
      <div className="toast-region" role="status" aria-live="polite" aria-atomic="true">{toast && <div className="toast"><Icon name="check" /><span>{toast.message}</span><button className="icon-button" aria-label="Fechar confirmação de cargo" onClick={() => setToast(null)}><Icon name="close" /></button></div>}</div>
      {dialog && <Modal variant={dialog.kind === "remove" ? "default" : "form"} title={dialog.kind === "add" ? "Adicionar cargo" : dialog.kind === "edit" ? "Editar cargo" : "Remover cargo"} busy={busy} onClose={() => setDialog(null)}>
        {dialog.kind === "remove" ? <><p className="modal-description">Remover <strong>{dialog.role.nome}</strong> e suas variações do cadastro?</p>{error && <p className="form-error" role="alert">{error}</p>}<div className="modal-actions"><button className="button button-secondary" disabled={busy} onClick={() => setDialog(null)}>Cancelar</button><button className="button button-danger" disabled={busy} onClick={() => void remove()}>{busy ? "Removendo…" : "Remover cargo"}</button></div></> : <form onSubmit={save}><p className="modal-description">O título pode conter o cargo em qualquer posição. Adicione as abreviações e variações que você aceita.</p><div className="field"><label htmlFor="role-name">Nome do cargo</label><input data-autofocus id="role-name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Ex.: Desenvolvedor" required maxLength={120} disabled={busy} /></div><div className="field"><label htmlFor="role-variations">Variações aceitas (opcional)</label><textarea id="role-variations" className="role-variations" value={variations} onChange={(event) => setVariations(event.target.value)} placeholder={'Dev\nDeveloper\nDesenvolvedora'} maxLength={4000} disabled={busy} aria-describedby="role-variations-hint" /><p id="role-variations-hint" className="implementation-note">Uma por linha ou separadas por vírgula. Até 30 variações; acentos, caixa e separadores simples são ignorados.</p></div><label className="role-selection-label"><input type="checkbox" checked={selected} onChange={(event) => setSelected(event.target.checked)} disabled={busy} /> Incluir este cargo nas buscas</label><p className="implementation-note">“Dev” corresponde a “Dev Backend”, mas não a “DevOps”. A busca considera apenas o título da vaga.</p>{error && <p className="form-error" role="alert">{error}</p>}<div className="modal-actions"><button type="button" className="button button-secondary" onClick={() => setDialog(null)} disabled={busy}>Cancelar</button><button className="button button-primary" disabled={busy}>{busy ? "Salvando…" : "Salvar cargo"}</button></div></form>}
      </Modal>}
    </section>
  );
}
