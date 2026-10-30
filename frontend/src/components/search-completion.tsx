"use client";

import { useState } from "react";

import { Icon } from "@/components/icon";
import { Modal } from "@/components/modal";
import { jobLink, type SearchStatus } from "@/lib/search-api";

export function SearchCompletion({ search }: { search: SearchStatus }) {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const failures = (search.diagnostics ?? search.source_validations ?? []).filter((item) => {
    const status = item.collection_status ?? item.status;
    return status ? status !== "concluida" && status !== "consultando" : item.support_status !== "compatible";
  });

  return (
    <>
      <div className={`search-completion${failures.length ? " search-completion-with-failures" : ""}`}>
        <p className="completion-message" role="status">
          <Icon name="check" />
          <span>Pesquisa finalizada: <strong>{search.found_count} {search.found_count === 1 ? "vaga encontrada" : "vagas encontradas"}</strong>.</span>
        </p>
        {failures.length > 0 && <div className="search-failure-message">
          <Icon name="warning" />
          <p role="status"><strong>{failures.length} {failures.length === 1 ? "site apresentou falha" : "sites apresentaram falhas"}</strong> na busca.</p>
          <button type="button" className="search-failure-details" onClick={() => setDetailsOpen(true)} aria-haspopup="dialog">Saber mais</button>
        </div>}
      </div>
      {detailsOpen && <Modal title="Sites com falha na busca" variant="diagnostics" onClose={() => setDetailsOpen(false)}>
        <p className="modal-description">Não foi possível consultar completamente os sites abaixo. As vagas encontradas nos demais portais continuam disponíveis; coletas parciais também podem ter retornado vagas.</p>
        <ul className="search-failures-list" aria-label="Empresas e motivos das falhas">
          {failures.map((item) => {
            const url = item.url ?? item.resolved_url ?? "";
            const href = jobLink(url);
            return <li key={item.id}>
              <div className="search-failure-company"><h3>{item.company}</h3><span aria-hidden="true">—</span>{href ? <a href={href} target="_blank" rel="noreferrer">{url}<span className="sr-only"> (abre em outra aba)</span></a> : <span>{url || "Site não informado"}</span>}</div>
              <p><strong>Motivo da falha:</strong> {item.message || "Não foi possível concluir a consulta deste site."}</p>
            </li>;
          })}
        </ul>
      </Modal>}
    </>
  );
}
