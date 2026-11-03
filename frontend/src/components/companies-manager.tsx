"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";

import { Icon } from "@/components/icon";
import { Modal } from "@/components/modal";
import { requestApi } from "@/lib/search-api";

type Company = { id: string; nome: string; url: string };
type CompanyData = Omit<Company, "id">;
type ExportDocument = { versao: 1; empresas: CompanyData[] };
type ImportPreview = { empresas: CompanyData[]; erros: { linha: number; motivo: string }[]; duplicadas: number };
type DialogState = { kind: "add" } | { kind: "edit"; company: Company } | { kind: "remove"; company: Company } | { kind: "export" } | { kind: "import" };

function message(error: unknown) { return error instanceof Error ? error.message : "Não foi possível concluir a operação. Tente novamente."; }

export function CompaniesManager({ onChanged }: { onChanged: () => void }) {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [filter, setFilter] = useState("");
  const [dialog, setDialog] = useState<DialogState | null>(null);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [pendingCompanies, setPendingCompanies] = useState<(CompanyData & { key: string })[]>([]);
  const companyNameInput = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [jsonText, setJsonText] = useState("");
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [toast, setToast] = useState<{ message: string } | null>(null);
  const [copied, setCopied] = useState(false);
  const copySource = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    requestApi<Company[]>("/api/companies", { signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setCompanies(data); })
      .catch((failure) => { if (!controller.signal.aborted) setLoadError(message(failure)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 4500);
    return () => clearTimeout(timer);
  }, [toast]);

  async function refresh() {
    setLoading(true);
    try {
      setCompanies(await requestApi<Company[]>("/api/companies"));
      setLoadError("");
    } catch (failure) { setLoadError(message(failure)); }
    finally { setLoading(false); }
  }

  function open(next: DialogState) {
    setError("");
    setPreview(null);
    setJsonText("");
    setCopied(false);
    setPendingCompanies([]);
    setName(next.kind === "edit" ? next.company.nome : "");
    setUrl(next.kind === "edit" ? next.company.url : "");
    setDialog(next);
  }

  function confirmed(text: string) {
    setToast({ message: text });
    onChanged();
    setDialog(null);
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (dialog?.kind !== "edit" || busy) return;
    if (!name.trim() || !url.trim()) { setError("Preencha o nome e o link da empresa."); return; }
    setBusy(true);
    setError("");
    try {
      const saved = await requestApi<Company>(`/api/companies/${encodeURIComponent(dialog.company.id)}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nome: name.trim(), url: url.trim() }),
      });
      setCompanies((current) => current.map((item) => item.id === saved.id ? saved : item));
      confirmed("Empresa atualizada com sucesso.");
    } catch (failure) { setError(message(failure)); }
    finally { setBusy(false); }
  }

  function queueCompany(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setError("");
    const entry = { nome: name.trim(), url: url.trim() };
    if (!entry.nome || !entry.url) { setError("Preencha o nome e o link da empresa."); return; }
    try {
      const parsed = new URL(entry.url);
      if (!["http:", "https:"].includes(parsed.protocol) || parsed.username || parsed.password || /\s|\\/.test(entry.url)) throw new Error();
    } catch { setError("Informe um link HTTP ou HTTPS válido, sem credenciais ou espaços."); return; }
    const signature = (item: CompanyData) => `${normalized(item.nome).replace(/\s+/g, " ")}|${new URL(item.url).href}`;
    if ([...companies, ...pendingCompanies].some((item) => signature(item) === signature(entry))) {
      setError("Esta empresa com esse link já está cadastrada ou na lista para adicionar."); return;
    }
    if (companies.length + pendingCompanies.length >= 10000) { setError("O cadastro atingiu o limite de 10.000 empresas."); return; }
    setPendingCompanies((current) => [...current, { ...entry, key: crypto.randomUUID() }]);
    setName(""); setUrl("");
    companyNameInput.current?.focus();
  }

  async function saveBatch() {
    if (busy || !pendingCompanies.length) return;
    if (name.trim() || url.trim()) {
      setError("Clique em Adicionar para incluir os campos preenchidos na lista antes de salvar.");
      companyNameInput.current?.focus();
      return;
    }
    setBusy(true); setError("");
    try {
      const saved = await requestApi<Company[]>("/api/companies/batch", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ empresas: pendingCompanies.map(({ nome, url }) => ({ nome, url })) }),
      });
      setCompanies((current) => [...current, ...saved]);
      confirmed(`${saved.length} ${saved.length === 1 ? "empresa cadastrada" : "empresas cadastradas"} com sucesso.`);
    } catch (failure) { setError(message(failure)); }
    finally { setBusy(false); }
  }

  async function remove() {
    if (dialog?.kind !== "remove" || busy) return;
    setBusy(true);
    setError("");
    try {
      await requestApi(`/api/companies/${encodeURIComponent(dialog.company.id)}`, { method: "DELETE" });
      setCompanies((current) => current.filter((item) => item.id !== dialog.company.id));
      confirmed("Empresa removida com sucesso.");
    } catch (failure) { setError(message(failure)); }
    finally { setBusy(false); }
  }

  async function exportJson() {
    open({ kind: "export" });
    setBusy(true);
    try {
      const data = await requestApi<ExportDocument>("/api/companies/export");
      setJsonText(JSON.stringify(data, null, 2));
    } catch (failure) { setError(message(failure)); }
    finally { setBusy(false); }
  }

  async function copyJson() {
    try {
      await navigator.clipboard.writeText(jsonText);
      setCopied(true);
      setToast({ message: "JSON formatado copiado." });
    } catch {
      copySource.current?.focus();
      copySource.current?.select();
      setError("Não foi possível copiar automaticamente. O texto foi selecionado; use Ctrl+C.");
    }
  }

  function downloadJson() {
    if (busy || !jsonText) return;
    const objectUrl = URL.createObjectURL(new Blob([jsonText], { type: "application/json;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = "rapidjobsearch-empresas.json";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
    setToast({ message: "Arquivo JSON preparado para salvar." });
  }

  async function previewImport() {
    setError("");
    setPreview(null);
    let document: unknown;
    try { document = JSON.parse(jsonText.replace(/^\uFEFF/, "")); }
    catch { setError("JSON inválido. Confira as aspas, vírgulas e chaves do arquivo."); return; }
    setBusy(true);
    try {
      setPreview(await requestApi<ImportPreview>("/api/companies/import/preview", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(document) }));
    } catch (failure) { setError(message(failure)); }
    finally { setBusy(false); }
  }

  async function importJson() {
    if (!preview || busy) return;
    setBusy(true);
    setError("");
    try {
      const result = await requestApi<{ importadas: number; duplicadas: number }>("/api/companies/import", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ versao: 1, empresas: preview.empresas }) });
      await refresh();
      confirmed(`${result.importadas} ${result.importadas === 1 ? "empresa importada" : "empresas importadas"} com sucesso.${result.duplicadas ? ` ${result.duplicadas} duplicada(s) ignorada(s).` : ""}`);
    } catch (failure) { setError(message(failure)); }
    finally { setBusy(false); }
  }

  const normalized = (value: string) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR");
  const filtered = companies.filter((company) => normalized(company.nome).includes(normalized(filter.trim())));
  const title = dialog?.kind === "add" ? "Adicionar empresa" : dialog?.kind === "edit" ? "Editar empresa" : dialog?.kind === "remove" ? "Remover empresa" : dialog?.kind === "export" ? "Exportar empresas em JSON" : "Importar empresas em JSON";

  return (
    <section id="empresas" className="card companies-card" aria-labelledby="companies-title">
      <div className="card-heading"><span className="section-icon"><Icon name="building" /></span><div><h3 id="companies-title">Suas empresas</h3><p>Gerencie os portais que você acompanha.</p></div><button className="button button-primary button-small add-company" onClick={() => open({ kind: "add" })} disabled={loading || !!loadError}><Icon name="plus" /> Adicionar empresa</button></div>
      <div className="field company-filter"><label htmlFor="company-search">Buscar empresa</label><div className="input-with-icon"><Icon name="search" /><input id="company-search" type="search" placeholder="Filtrar pelo nome da empresa" value={filter} onChange={(event) => setFilter(event.target.value)} /></div></div>
      <div className="company-list-caption" aria-live="polite">{loading ? "Carregando empresas…" : loadError ? "Cadastro indisponível" : `${companies.length} ${companies.length === 1 ? "empresa cadastrada" : "empresas cadastradas"}${filter.trim() ? ` · ${filtered.length} no filtro` : ""}`}</div>
      {loadError && <div className="form-error" role="alert">{loadError} <button className="text-link" onClick={() => void refresh()}>Tentar novamente</button></div>}
      <div className="company-list" tabIndex={0} role="region" aria-label="Empresas cadastradas" aria-busy={loading} onScroll={(event) => event.currentTarget.querySelectorAll<HTMLElement>("[popover]:popover-open").forEach((element) => element.hidePopover())}>
        {!loading && !loadError && filtered.length === 0 && <div className="companies-empty"><Icon name="building" /><h4>{companies.length ? "Nenhuma empresa corresponde ao filtro" : "Sua lista de empresas começa aqui"}</h4><p>{companies.length ? "Tente outro nome ou limpe a pesquisa." : "Adicione sua primeira empresa ou importe uma lista em JSON."}</p>{companies.length > 0 && <button className="text-link" onClick={() => setFilter("")}>Limpar filtro</button>}</div>}
        <ul className="company-rows">{filtered.map((company) => <li className="company-row" key={company.id}>
          <span className="company-name" title={company.nome}>{company.nome}</span>
          <a className="company-url" href={company.url} title={company.url} target="_blank" rel="noreferrer">{company.url}</a>
          <button className="icon-button company-actions-trigger" popoverTarget={`company-actions-${company.id}`} aria-label={`Ações de ${company.nome}`} onClick={(event) => { const box = event.currentTarget.getBoundingClientRect(); const element = document.getElementById(`company-actions-${company.id}`); element?.style.setProperty("--menu-left", `${Math.max(8, box.right - 150)}px`); element?.style.setProperty("--menu-top", `${Math.min(window.innerHeight - 110, box.bottom + 5)}px`); }}><Icon name="more" /></button>
          <div popover="auto" id={`company-actions-${company.id}`} className="company-actions-menu" onToggle={(event) => { if (event.currentTarget.matches(":popover-open")) event.currentTarget.querySelector<HTMLButtonElement>("button")?.focus(); }} role="menu" aria-label={`Opções de ${company.nome}`} onKeyDown={(event) => { if (["ArrowDown", "ArrowUp"].includes(event.key)) { event.preventDefault(); const buttons = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>("button")); const index = buttons.indexOf(document.activeElement as HTMLButtonElement); buttons[(index + (event.key === "ArrowDown" ? 1 : -1) + buttons.length) % buttons.length]?.focus(); } }}>
            <button role="menuitem" onClick={() => { document.getElementById(`company-actions-${company.id}`)?.hidePopover(); open({ kind: "edit", company }); }}><Icon name="edit" /> Editar</button>
            <button role="menuitem" className="danger-text" onClick={() => { document.getElementById(`company-actions-${company.id}`)?.hidePopover(); open({ kind: "remove", company }); }}><Icon name="trash" /> Remover</button>
          </div>
        </li>)}</ul>
      </div>
      <div className="import-actions"><span>Compartilhe sua lista em JSON</span><div><button className="button button-secondary button-small" onClick={() => open({ kind: "import" })} disabled={loading || !!loadError}><Icon name="upload" /> Importar JSON</button><button className="button button-secondary button-small" onClick={() => void exportJson()} disabled={loading || !!loadError}><Icon name="download" /> Exportar JSON</button></div></div>
      <p className="implementation-note">As empresas ficam salvas no servidor. A exportação inclui toda a lista, mesmo com um filtro ativo.</p>

      <div className="toast-region" role="status" aria-live="polite" aria-atomic="true">{toast && <div className="toast"><Icon name="check" /><span>{toast.message}</span><button className="icon-button" aria-label="Fechar confirmação" onClick={() => setToast(null)}><Icon name="close" /></button></div>}</div>

      {dialog && <Modal
        variant={dialog.kind === "add" ? "batch" : dialog.kind === "import" || dialog.kind === "export" ? "document" : dialog.kind === "remove" ? "confirmation" : "form"}
        title={title}
        onClose={() => setDialog(null)}
        busy={busy}
        footer={dialog.kind === "remove" ? <div className="modal-actions">
          <button type="button" data-autofocus className="button button-secondary" onClick={() => setDialog(null)} disabled={busy}>Cancelar</button>
          <button type="button" className="button button-danger" onClick={() => void remove()} disabled={busy}>{busy ? "Removendo…" : "Remover empresa"}</button>
        </div> : dialog.kind === "add" ? <div className="batch-footer">
          <p className="modal-footer-note" role="status">{pendingCompanies.length} {pendingCompanies.length === 1 ? "empresa para adicionar" : "empresas para adicionar"}</p>
          <button className="button button-primary" onClick={() => void saveBatch()} disabled={busy || !pendingCompanies.length}><Icon name="check" />{busy ? "Salvando…" : "Salvar"}</button>
        </div> : dialog.kind === "export" ? <>
          <p className="modal-footer-note">Lista completa, pronta para compartilhar.</p>
          <div className="modal-actions">
            <button className="button button-secondary" onClick={() => setDialog(null)} disabled={busy}>Fechar</button>
            <button className="button button-secondary" onClick={() => void copyJson()} disabled={busy || !jsonText}><Icon name="copy" />{copied ? "JSON copiado!" : "Copiar JSON"}</button>
            <button className="button button-primary" onClick={downloadJson} disabled={busy || !jsonText}><Icon name="download" />Salvar JSON</button>
          </div>
        </> : dialog.kind === "import" ? <>
          <p className="modal-footer-note">{preview ? "Confira a revisão antes de salvar as empresas." : "Revise o conteúdo antes de importar."}</p>
          <div className="modal-actions">
            <button className="button button-secondary" onClick={() => setDialog(null)} disabled={busy}>Cancelar</button>
            {preview ? <button className="button button-primary" onClick={() => void importJson()} disabled={busy || !preview.empresas.length}><Icon name="check" />{busy ? "Salvando…" : `Salvar ${preview.empresas.length} ${preview.empresas.length === 1 ? "empresa" : "empresas"}`}</button> : <button className="button button-primary" onClick={() => void previewImport()} disabled={busy || !jsonText.trim()}><Icon name="upload" />{busy ? "Validando…" : "Revisar importação"}</button>}
          </div>
        </> : undefined}
      >
        {dialog.kind === "add" && <>
          <p className="modal-description">Preencha os dados e clique em Adicionar. Monte sua lista e salve todas as empresas ao finalizar.</p>
          <form className="batch-company-form" onSubmit={queueCompany}>
            <div className="field"><label htmlFor="batch-company-name">Nome da empresa</label><input ref={companyNameInput} data-autofocus id="batch-company-name" placeholder="Ex.: Nome da empresa" maxLength={200} required value={name} onChange={(event) => setName(event.target.value)} disabled={busy} /></div>
            <div className="field"><label htmlFor="batch-company-url">Link da empresa</label><input id="batch-company-url" type="url" placeholder="https://empresa.com/carreiras" maxLength={2048} required value={url} onChange={(event) => setUrl(event.target.value)} disabled={busy} /></div>
            <button type="submit" className="button button-secondary" disabled={busy}><Icon name="plus" />Adicionar</button>
          </form>
          {error && <p className="form-error" role="alert">{error}</p>}
          <div className="batch-list-heading"><h3>Empresas a adicionar</h3><span>Salvas somente ao finalizar</span></div>
          <div className="batch-company-list" role="region" aria-label="Empresas a adicionar" tabIndex={0}>
            {pendingCompanies.length ? <ul>{pendingCompanies.map((company) => <li key={company.key}>
              <div><strong>{company.nome}</strong><span>{company.url}</span></div>
              <button className="icon-button" aria-label={`Remover ${company.nome} da lista`} disabled={busy} onClick={() => { setPendingCompanies((current) => current.filter((item) => item.key !== company.key)); setError(""); }}><Icon name="close" /></button>
            </li>)}</ul> : <div className="batch-list-empty"><Icon name="building" /><p>As empresas adicionadas aparecerão aqui.</p></div>}
          </div>
        </>}
        {dialog.kind === "edit" && <form onSubmit={save}>
          <p className="modal-description">Informe o nome e o endereço do portal de carreiras da empresa.</p>
          <div className="field"><label htmlFor="company-name">Nome da empresa</label><input data-autofocus id="company-name" placeholder="Ex.: Nome da empresa" maxLength={200} required value={name} onChange={(event) => setName(event.target.value)} disabled={busy} /></div>
          <div className="field"><label htmlFor="company-url">Link da empresa</label><input id="company-url" type="url" placeholder="https://empresa.com/carreiras" maxLength={2048} required value={url} onChange={(event) => setUrl(event.target.value)} disabled={busy} /></div>
          {error && <p className="form-error" role="alert">{error}</p>}
          <div className="modal-actions"><button type="button" className="button button-secondary" onClick={() => setDialog(null)} disabled={busy}>Cancelar</button><button type="submit" className="button button-primary" disabled={busy}>{busy ? "Salvando…" : "Salvar empresa"}</button></div>
        </form>}
        {dialog.kind === "remove" && <>
          <p className="modal-description">Ao remover <strong>{dialog.company.nome}</strong>, a empresa não será mais consultada e suas vagas deixarão de aparecer nas próximas buscas.</p>
          <p className="modal-hint">Os resultados das pesquisas já realizadas serão mantidos. Você poderá cadastrar a empresa novamente depois.</p>
          {error && <p className="form-error" role="alert">{error}</p>}
        </>}
        {dialog.kind === "export" && <>
          <p className="modal-description">Salve o arquivo ou copie o JSON formatado para compartilhar sua lista completa de empresas.</p>
          <div className="json-panel-heading"><label className="field-label" htmlFor="export-json">Prévia da exportação</label><span className="badge badge-neutral">JSON · UTF-8</span></div>
          <textarea ref={copySource} id="export-json" className="json-editor" readOnly value={busy ? "Carregando lista…" : jsonText} spellCheck={false} aria-busy={busy} />
          {error && <p className="form-error" role="alert">{error}</p>}
        </>}
        {dialog.kind === "import" && <>
          <p className="modal-description">Escolha um arquivo ou cole o JSON abaixo. Sua lista atual será mantida e empresas duplicadas serão ignoradas.</p>
          <div className="field json-file-field">
            <label htmlFor="import-file"><Icon name="upload" />Selecionar arquivo JSON</label>
            <p id="import-file-hint">Arquivo .json de até 2 MB.</p>
            <input data-autofocus id="import-file" type="file" accept=".json,application/json" aria-describedby="import-file-hint" disabled={busy} onChange={async (event) => {
              const file = event.target.files?.[0];
              if (!file) return;
              setError(""); setPreview(null);
              if (file.size > 2 * 1024 * 1024) { setJsonText(""); setError("O arquivo deve ter no máximo 2 MB."); return; }
              try { setJsonText(await file.text()); } catch { setError("Não foi possível ler o arquivo selecionado."); }
            }} />
          </div>
          <div className="json-panel-heading"><label className="field-label" htmlFor="import-json">Conteúdo JSON</label><span className="badge badge-neutral">Cole ou edite a lista</span></div>
          <textarea id="import-json" className="json-editor" value={jsonText} onChange={(event) => { setJsonText(event.target.value); setPreview(null); setError(""); }} disabled={busy} maxLength={2 * 1024 * 1024} placeholder={'{\n  "versao": 1,\n  "empresas": [\n    { "nome": "Nome da empresa", "url": "https://empresa.com/carreiras" }\n  ]\n}'} spellCheck={false} />
          {preview && <div className="import-preview" role="status"><strong>Revisão da importação</strong><p>{preview.empresas.length} para adicionar · {preview.duplicadas} duplicadas · {preview.erros.length} inválidas</p>{preview.erros.length > 0 && <ul>{preview.erros.map((item) => <li key={item.linha}>Empresa {item.linha}: {item.motivo}</li>)}</ul>}{preview.empresas.length > 0 && <ul className="import-valid-list">{preview.empresas.map((item) => <li key={`${item.nome}|${item.url}`}>{item.nome} <span>{item.url}</span></li>)}</ul>}</div>}
          {error && <p className="form-error" role="alert">{error}</p>}
        </>}
      </Modal>}
    </section>
  );
}
