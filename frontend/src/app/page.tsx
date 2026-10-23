import { EnvironmentStatus } from "@/components/environment-status";

const iconPaths = {
  search: "m21 21-4.5-4.5M19 10.5a8.5 8.5 0 1 1-17 0 8.5 8.5 0 0 1 17 0Z",
  building: "M4 21V5a1 1 0 0 1 1-1h10v17M15 10h4a1 1 0 0 1 1 1v10M2 21h20M8 8h3M8 12h3M8 16h3",
  sliders: "M4 7h16M4 17h16M8 4v6M16 14v6",
  arrow: "M5 12h14m-5-5 5 5-5 5",
  globe: "M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM3 12h18M12 3c5 5 5 13 0 18-5-5-5-13 0-18Z",
  plus: "M12 5v14M5 12h14",
  download: "M12 3v12m-4-4 4 4 4-4M4 16v5h16v-5",
  upload: "M12 16V4m-4 4 4-4 4 4M4 16v5h16v-5",
  briefcase: "M8 7V4h8v3M3 7h18v14H3V7Zm0 6a22 22 0 0 0 18 0M10 13h4v3h-4v-3Z",
  check: "m5 12 4 4L19 6",
};

function Icon({ name, className = "" }: { name: keyof typeof iconPaths; className?: string }) {
  return (
    <svg className={`icon ${className}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={iconPaths[name]} />
    </svg>
  );
}

export default function Home() {
  return (
    <>
      <a className="skip-link" href="#conteudo">Ir para o conteúdo</a>
      <header className="app-header">
        <div className="header-inner">
          <a className="brand" href="#conteudo" aria-label="RapidJobSearch, início">
            <span className="brand-mark"><Icon name="search" /></span>
            <span>Rapid<span className="brand-accent">Job</span>Search</span>
          </a>
          <nav className="main-nav" aria-label="Navegação principal">
            <a href="#empresas">Empresas</a>
            <a href="#palavras-chave">Palavras-chave</a>
            <a href="#resultados">Resultados</a>
          </nav>
          <span className="badge badge-neutral header-badge">Seu painel de vagas</span>
        </div>
      </header>

      <main id="conteudo" className="app-main">
        <div className="preview-notice"><span className="status-dot" /><strong>Prévia do painel</strong><span>O layout está pronto para receber as funcionalidades das próximas etapas.</span></div>

        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-copy">
            <span className="eyebrow">MENOS ABAS. MAIS OPORTUNIDADES.</span>
            <h1 id="hero-title">Sua próxima vaga remota<br className="desktop-break" /> começa por aqui.</h1>
            <p>Reúna as empresas que você acompanha, escolha o que procura e encontre suas oportunidades em um só lugar.</p>
            <a href="#empresas" className="button button-light">Preparar minha busca <Icon name="arrow" /></a>
          </div>
          <div className="hero-aside">
            <span className="hero-globe"><Icon name="globe" /></span>
            <span className="badge badge-hero"><span className="status-dot" /> Somente vagas remotas</span>
            <p>Direto dos portais<br />das suas empresas favoritas.</p>
          </div>
        </section>

        <div className="section-intro"><div><span className="eyebrow">DO SEU JEITO</span><h2>Prepare sua pesquisa</h2></div><p>Empresas + palavras-chave. É por aqui que tudo começa.</p></div>

        <div className="configuration-grid">
          <section id="empresas" className="card" aria-labelledby="companies-title">
            <div className="card-heading"><span className="section-icon"><Icon name="building" /></span><div><h3 id="companies-title">Suas empresas</h3><p>Escolha onde você quer trabalhar.</p></div><span className="step-label">01</span></div>
            <div className="field-preview" aria-describedby="companies-note">
              <div className="form-grid"><div className="field"><label htmlFor="company-name">Nome da empresa</label><input id="company-name" placeholder="Ex.: Empresa que você acompanha" disabled /></div><div className="field"><label htmlFor="company-url">Link de carreiras</label><input id="company-url" type="url" placeholder="https://empresa.com/carreiras" disabled /></div></div>
              <button className="button button-primary button-full" disabled><Icon name="plus" /> Adicionar empresa</button>
            </div>
            <div className="import-actions"><span>Compartilhe sua lista em JSON</span><div><button className="button button-secondary button-small" disabled><Icon name="upload" /> Importar</button><button className="button button-secondary button-small" disabled><Icon name="download" /> Exportar</button></div></div>
            <p className="implementation-note" id="companies-note">Cadastro e arquivos JSON serão conectados nas etapas 2 e 3.</p>
          </section>

          <section id="palavras-chave" className="card" aria-labelledby="keywords-title">
            <div className="card-heading"><span className="section-icon"><Icon name="sliders" /></span><div><h3 id="keywords-title">O que você procura?</h3><p>Defina os termos que devem aparecer no título.</p></div><span className="step-label">02</span></div>
            <div className="field"><label htmlFor="keyword">Palavra-chave</label><div className="keyword-input"><input id="keyword" placeholder="Digite um termo de vaga" disabled /><button className="button button-primary" disabled aria-label="Adicionar palavra-chave"><Icon name="plus" /></button></div></div>
            <div className="keyword-examples"><span className="field-label">Exemplos de termos</span><div className="chip-list"><span className="chip">fullstack</span><span className="chip">backend</span><span className="chip">frontend</span></div><p>Um dos termos no nome da vaga já é suficiente. Esses exemplos ainda não estão cadastrados.</p></div>
            <div className="remote-rule"><span className="remote-rule-icon"><Icon name="check" /></span><div><strong>Somente trabalho remoto</strong><p>Vagas presenciais e híbridas ficam fora da busca.</p></div></div>
            <p className="implementation-note">Palavras-chave e regras serão conectadas na etapa 4.</p>
          </section>
        </div>

        <section className="search-bar" aria-labelledby="search-title"><div><h2 id="search-title">Tudo pronto para a próxima oportunidade?</h2><p>Durante a pesquisa, você acompanhará a quantidade de vagas encontradas.</p><span className="implementation-note">Pesquisa disponível após a integração do primeiro portal e do processamento em segundo plano.</span></div><button className="button button-primary search-button" disabled><Icon name="search" /> Realizar pesquisa</button></section>

        <section id="resultados" className="card results-card" aria-labelledby="results-title">
          <div className="results-heading"><div><span className="eyebrow">SUAS OPORTUNIDADES</span><h2 id="results-title">Vagas encontradas</h2></div><span className="badge badge-remote"><Icon name="globe" /> Remotas</span></div>
          <div className="table-scroll"><table className="jobs-table"><caption className="sr-only">Oportunidades encontradas na pesquisa, por empresa e nome da vaga.</caption><thead><tr><th scope="col">Empresa</th><th scope="col">Nome da vaga</th></tr></thead><tbody><tr><td colSpan={2}><div className="empty-state"><span className="empty-icon"><Icon name="briefcase" /></span><h3>Sua lista de oportunidades começa aqui</h3><p>Quando a pesquisa estiver disponível, suas vagas aparecerão nesta tabela, com links diretos para os anúncios.</p><span className="empty-hint">Sem pesquisa realizada · Listagem paginada na etapa 7</span></div></td></tr></tbody></table></div>
        </section>

        <EnvironmentStatus />
        <footer className="app-footer"><span>RapidJobSearch</span><p>Seu próximo passo profissional, com menos procura.</p><span>Feito para simplificar.</span></footer>
      </main>
    </>
  );
}
