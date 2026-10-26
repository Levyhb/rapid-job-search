"use client";

import { useRef, useState, type KeyboardEvent } from "react";

import { CompaniesManager } from "@/components/companies-manager";
import { EnvironmentStatus } from "@/components/environment-status";
import { Icon } from "@/components/icon";
import { RolesManager } from "@/components/roles-manager";
import { SearchPanel } from "@/components/search-panel";

type Tab = "search" | "configuration";

export default function Home() {
  const [companiesRevision, setCompaniesRevision] = useState(0);
  const [tab, setTab] = useState<Tab>("search");
  const searchTab = useRef<HTMLButtonElement>(null);
  const configurationTab = useRef<HTMLButtonElement>(null);

  function selectTab(next: Tab, focus = false) {
    setTab(next);
    window.scrollTo({ top: 0, behavior: "instant" });
    if (focus) (next === "search" ? searchTab : configurationTab).current?.focus();
  }

  function navigateTabs(event: KeyboardEvent<HTMLButtonElement>) {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === "Home" ? "search" : event.key === "End" ? "configuration" : tab === "search" ? "configuration" : "search";
    selectTab(next, true);
  }

  return (
    <>
      <a className="skip-link" href="#conteudo">Ir para o conteúdo</a>
      <header className="app-header">
        <div className="header-inner">
          <button className="brand" onClick={() => selectTab("search")} aria-label="RapidJobSearch, início">
            <span className="brand-mark"><Icon name="search" /></span>
            <span>Rapid<span className="brand-accent">Job</span>Search</span>
          </button>
          <div className="main-nav workspace-tabs" role="tablist" aria-label="Áreas do painel">
            <button ref={searchTab} id="search-tab" role="tab" aria-selected={tab === "search"} aria-controls="search-panel" tabIndex={tab === "search" ? 0 : -1} onClick={() => selectTab("search")} onKeyDown={navigateTabs}><Icon name="search" /> Busca por vagas</button>
            <button ref={configurationTab} id="configuration-tab" role="tab" aria-selected={tab === "configuration"} aria-controls="configuration-panel" tabIndex={tab === "configuration" ? 0 : -1} onClick={() => selectTab("configuration")} onKeyDown={navigateTabs}><Icon name="sliders" /> Empresas e cargos</button>
          </div>
          <span className="badge badge-neutral header-badge">Seu painel de vagas</span>
        </div>
      </header>

      <main id="conteudo" className="app-main">
        <div className="preview-notice"><span className="status-dot" /><strong>Busca de vagas remotas</strong><span>Consulte as empresas cadastradas usando seus cargos e variações.</span></div>
        <section id="search-panel" role="tabpanel" aria-labelledby="search-tab" hidden={tab !== "search"} tabIndex={0}>
          <section className="hero" aria-labelledby="hero-title">
            <div className="hero-copy">
              <span className="eyebrow">MENOS ABAS. MAIS OPORTUNIDADES.</span>
              <h1 id="hero-title">Sua próxima vaga remota<br className="desktop-break" /> começa por aqui.</h1>
              <p>Consulte as empresas que você acompanha e encontre as vagas remotas dos cargos que selecionou.</p>
              <button onClick={() => selectTab("configuration", true)} className="button button-light">Configurar empresas e cargos <Icon name="arrow" /></button>
            </div>
            <div className="hero-aside">
              <span className="hero-globe"><Icon name="globe" /></span>
              <span className="badge badge-hero"><span className="status-dot" /> Somente vagas remotas</span>
              <p>Direto dos portais<br />das suas empresas favoritas.</p>
            </div>
          </section>
          <div className="section-intro"><div><span className="eyebrow">SUA BUSCA, DO SEU JEITO</span><h2>Busca por vagas</h2></div><p>Confira sua configuração e encontre novas oportunidades.</p></div>
          <SearchPanel companiesRevision={companiesRevision} active={tab === "search"} onConfigure={() => selectTab("configuration", true)} />
        </section>

        <section id="configuration-panel" role="tabpanel" aria-labelledby="configuration-tab" hidden={tab !== "configuration"} tabIndex={0}>
          <div className="configuration-intro"><span className="eyebrow">PREPARE SUA PRÓXIMA OPORTUNIDADE</span><h1>Empresas e cargos</h1><p>Defina onde você quer trabalhar e quais cargos deseja encontrar. Depois, volte à aba de busca para pesquisar.</p></div>
        <div className="configuration-grid">
          <CompaniesManager onChanged={() => setCompaniesRevision((revision) => revision + 1)} />

          <RolesManager onChanged={() => setCompaniesRevision((revision) => revision + 1)} />
        </div>


          <div className="configuration-return"><p>Sua pesquisa usará as empresas cadastradas e os cargos selecionados.</p><button className="button button-primary" onClick={() => selectTab("search", true)}>Ir para Busca por vagas <Icon name="arrow" /></button></div>
        </section>
        <EnvironmentStatus />
        <footer className="app-footer"><span>RapidJobSearch</span><p>Seu próximo passo profissional, com menos procura.</p><span>Feito para simplificar.</span></footer>
      </main>
    </>
  );
}
