() => {
  const visible = e => !!e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden';
  const clean = s => (s || '').replace(/\s+/g, ' ').trim();
  const readable = e => {
    // Conteúdo carregado oculto só pela animação pode ser lido sem acionar a interface.
    // Filtros reais (hidden/display:none/aria-hidden) continuam sendo respeitados.
    let animation = false;
    for (let p=e; p; p=p.parentElement || p.getRootNode()?.host) {
      if (p.hidden || p.getAttribute('aria-hidden') === 'true' || getComputedStyle(p).display === 'none') return false;
      if (p.matches('.wow,[data-aos],[data-animate]')) animation = true;
    }
    return visible(e) || (animation && !!e.getClientRects().length);
  };
  const roots = [document];
  for (let i=0; i<roots.length; i++) {
    for (const e of roots[i].querySelectorAll('*')) if (e.shadowRoot) roots.push(e.shadowRoot);
  }
  const all = selector => roots.flatMap(root => [...root.querySelectorAll(selector)]);
  const jobs = [];
  const handledCards = new Set();
  const handledTargets = new Set();
  const structured = value => {
    if (!value || typeof value !== 'object') return;
    if (Array.isArray(value)) return value.forEach(structured);
    if ([].concat(value['@type'] || []).includes('JobPosting')) {
      const place = value.jobLocation;
      jobs.push({title: value.title, url: value.url || location.href,
        text: clean(value.description), mode: value.jobLocationType || '',
        location: JSON.stringify(place || ''), structured: true});
    }
    if (value['@graph']) structured(value['@graph']);
  };
  for (const script of all('script[type="application/ld+json"]')) {
    try { structured(JSON.parse(script.textContent)); } catch { /* not a JobPosting */ }
  }
  const role = /\bdev\b|backend|frontend|full[ -]?stack|desenvolved|developer|engineer|engenheir|analista|analyst|designer|architect|arquiteto|programador|programmer|cientista|scientist|product manager|qa\b|estagi|intern\b|trainee/i;
  const jobPath = /\/(jobs?|vagas?|positions?|oportunidades|vacancies)\/.+/i;
  for (const a of all('a[href]')) {
    if (!/^https?:$/.test(a.protocol)) continue;
    if (a.closest('header,footer,nav,[role="navigation"]')) continue;
    const card = a.closest('tr,article,li,[class*="job-card"],[class*="vacancy"],[class*="vaga-item"],[class*="accordion-item"],[class*="job-item"],[class*="job-listing"]');
    const heading = card?.querySelector('[data-job-title],[class*="titulo"],[class*="title"],h2,h3,h4');
    // Accordions keep announcement links inside a hidden panel tied to a visible heading.
    const toggle = heading?.querySelector('[aria-controls]');
    const panel = toggle && document.getElementById(toggle.getAttribute('aria-controls'));
    if (!readable(a) && !(heading && readable(heading) && panel?.contains(a))) continue;
    const title = clean(heading?.textContent || a.textContent);
    if (!title || title.length > 240 || /apply now|candidatar|saiba mais|learn more/i.test(title)) continue;
    const jobCard = card && /job|vacancy|vaga|accordion-item/i.test(card.className);
    if (!role.test(title) && !jobPath.test(a.href) && !(jobCard && heading)) continue;
    if (a.href.split('#')[0] === location.href.split('#')[0]) continue;
    if (/^(vagas|jobs|oportunidades|careers|carreiras|ver vagas|open positions)$/i.test(title)) continue;
    const mode = card?.querySelector('[class*="workplace"],[class*="modality"],[class*="modalidade"],[data-workplace],[class*="vi-modelo"]');
    const local = card?.querySelector('[class*="location"],[class*="localidade"]');
    const cells = card?.tagName === 'TR' ? [...card.cells].map(c=>clean(c.textContent)) : [];
    const tableMode = cells.find(t=>/^(remot[oa]|remote|h[ií]brid[oa]|hybrid|presencial|on.?site|telecommute)$/i.test(t));
    const model = card?.dataset.modelo || card?.dataset.workplace || mode?.textContent || tableMode;
    jobs.push({title, url:a.href, text:visible(a) ? (card?.innerText || a.innerText) : (card?.textContent || a.textContent),
      mode:clean(model), location:clean(local?.textContent || (cells.length>=4 ? cells.at(-1) : '')),
      excluded:/banco de talentos|talent pool/i.test(title), structured:false});
    if (card) handledCards.add(card);
  }
  const listSelector = '[class*="vacancies-list"],[class*="job-list"],[class*="vagas-list"],[class*="job-results"],[data-job-list]';
  const cards = new Set(all('article,[class*="job-card"],[class*="vacancy-card"],[class*="vaga-item"],[class*="job-item"]'));
  for (const list of all(listSelector)) for (const child of list.children) cards.add(child);
  const openLabel = /^(acessar (?:a )?vaga|ver (?:a )?vaga|ver detalhes(?: da vaga)?|detalhes(?: da vaga)?|view (?:job|details)|job details|read more)\s*[›»→]?$/i;
  for (const card of cards) {
    if (handledCards.has(card) || !visible(card) || card.closest('header,footer,nav,form')) continue;
    const heading = card.querySelector('h2,h3,h4,[class*="title"]') || card.querySelector('p') ||
      card.querySelector('button,[role="button"],[onclick]');
    const title = clean(heading?.textContent);
    const inList = !!card.closest(listSelector);
    if (!title || title.length > 240 || (!role.test(title) && !inList)) continue;
    if (/banco de talentos|talent pool|candidat|apply now/i.test(title)) continue;
    const controls = [...card.querySelectorAll('button,[role="button"],a,span,div')];
    let target = controls.find(e => visible(e) && openLabel.test(clean(e.textContent)) &&
      ![...e.children].some(c => openLabel.test(clean(c.textContent))));
    if (!target && heading) target = heading.querySelector('button,[role="button"],a,[onclick]');
    if (!target && heading && (heading.matches('button,[role="button"],[onclick]') ||
        getComputedStyle(heading).cursor === 'pointer')) target = heading;
    if (!target && (card.matches('[role="button"],[onclick],[tabindex="0"]') ||
        (inList && getComputedStyle(card).cursor === 'pointer'))) target = card;
    if (!target || /candidat|apply|inscrev/i.test(clean(target.textContent))) continue;
    if (handledTargets.has(target)) continue;
    handledTargets.add(target);
    if (!/^\d+$/.test(target.dataset.rapidjobClick || '')) {
      window.__rapidjobClickSequence = (window.__rapidjobClickSequence || 0) + 1;
      target.dataset.rapidjobClick = String(window.__rapidjobClickSequence);
    }
    const mode = card.querySelector('[class*="workplace"],[class*="modality"],[class*="modalidade"]');
    const firstLine = clean(card.firstElementChild?.textContent);
    const location = card.querySelector('[class*="location"],[class*="localidade"]');
    const field = mode?.textContent || (firstLine !== title && firstLine.length < 180 &&
      /\b(remot[oa]|remote|h[ií]brid[oa]|hybrid|presencial|on.?site)\b/i.test(firstLine) ? firstLine : '');
    jobs.push({title, url:'', click:target.dataset.rapidjobClick, text:card.innerText,
      mode:clean(field), location:clean(location?.textContent || (field ? firstLine : '')), structured:false});
  }
  const empty = all('main p,main h2,main h3,[role="status"]')
    .some(e => visible(e) && /^(nenhuma vaga (disponível|encontrada)|no (open |available )?(jobs|positions|vacancies)( found| available)?|0 (vagas|jobs|positions))/i.test(clean(e.textContent)));
  const totals = new Set();
  for (const e of all('[class*="total"],[class*="count"],[id*="count"],[id*="total"],[role="status"]')) {
    if (!visible(e)) continue;
    const match = clean(e.textContent).match(/^(\d+)\s+(?:(?:vagas|jobs|positions)(?:\s+(?:encontradas|disponíveis|disponiveis|abertas|available))?|open positions)\.?$/i);
    if (match) totals.add(Number(match[1]));
  }
  for (const e of all('#jobs h2,#jobs h3,#jobs h4')) {
    const match = clean(e.textContent).match(/^(?:Nossas vagas|Our openings)\s*\((\d+)\)$/i);
    if (match) totals.add(Number(match[1]));
  }
  for (const e of all('span,p,[role="status"]')) {
    if (!visible(e) || e.children.length > 2) continue;
    const match = clean(e.textContent).match(/^Mostrando de \d+ a \d+ de (\d+) vagas$/i);
    if (match) totals.add(Number(match[1]));
  }
  return {jobs, empty, expected:totals.size === 1 ? [...totals][0] : null, title:document.title};
}
