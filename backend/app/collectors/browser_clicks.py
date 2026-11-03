"""Abre detalhes de cards sem href e restaura a listagem, sem clicar em candidatura."""

import re
import time
from urllib.parse import urlsplit

from playwright.sync_api import Error as BrowserError
from playwright.sync_api import TimeoutError as BrowserTimeout

from app.collectors.network import validate_target
from app.collectors.portals import SourceProblem

STATE = r"""({url,title}) => {
  const roots=[document];
  for(let i=0;i<roots.length;i++)for(const e of roots[i].querySelectorAll('*'))
    if(e.shadowRoot)roots.push(e.shadowRoot);
  const selector='dialog[open],[role="dialog"],[aria-modal="true"]';
  const dialogs=roots.flatMap(r=>[...r.querySelectorAll(selector)]);
  const dialog=dialogs.find(e=>e.getClientRects().length &&
    getComputedStyle(e).visibility!=='hidden' &&
    e.textContent.replace(/\s+/g,' ').toLowerCase().includes(title.toLowerCase()));
  if(dialog)dialog.dataset.rapidjobDialog='active';
  return {changed:location.href!==url,dialog:!!dialog};
}"""


def signature(snapshot):
    return [
        [j.get("title", ""), j.get("url", ""), (j.get("text") or "")[:200]]
        for j in snapshot["jobs"]
    ]


class ClickNavigator:
    def __init__(self, page, extract, navigate, remaining, wait_listing, advance):
        self.page, self.extract, self.navigate = page, extract, navigate
        self.remaining, self.wait_listing, self.advance = remaining, wait_listing, advance
        self.start_url = page.url

    def _signature_matches(self, snapshot, timeout):
        try:
            self.page.wait_for_function(
                f"expected => JSON.stringify(({self.extract})().jobs.map(j=>"
                "[j.title||'',j.url||'',(j.text||'').slice(0,200)])) === JSON.stringify(expected)",
                arg=signature(snapshot),
                timeout=timeout,
            )
            return True
        except BrowserTimeout:
            return False

    def _restore(self, url, snapshot, step):
        dialog = self.page.locator('[data-rapidjob-dialog="active"]:visible')
        if dialog.count():
            close = dialog.first.get_by_role(
                "button", name=re.compile(r"^(fechar|close|dismiss|[×x])$", re.I)
            )
            if close.count() == 1:
                close.click(timeout=self.remaining())
            else:
                self.page.keyboard.press("Escape")
            try:
                dialog.first.wait_for(state="hidden", timeout=min(self.remaining(), 1500))
            except BrowserTimeout:
                # Um modal que não fecha não pode interferir nos cliques seguintes.
                self.navigate(self.page, url, self.remaining())
        if self.page.url != url:
            try:
                self.page.go_back(wait_until="domcontentloaded", timeout=self.remaining())
            except BrowserError:
                pass
        if self._signature_matches(snapshot, min(self.remaining(), 2000)):
            return
        # Alguns SPAs voltam à primeira página. Reproduzir os avanços em vez de perder vagas.
        self.navigate(self.page, self.start_url, self.remaining())
        for _ in range(step):
            current = self.wait_listing(self.page, self.remaining())
            if not self.advance(self.page, current, self.remaining(), self.navigate):
                break
        if not self._signature_matches(snapshot, min(self.remaining(), 3000)):
            raise SourceProblem(
                "Não foi possível restaurar a página original da listagem.",
                "parcial",
                "listing_restore_failed",
            )

    def resolve(self, item, snapshot, index, step):
        original = self.page.url
        before = set(self.page.context.pages)
        # O Angular pode recriar os elementos ao voltar. Reencontrar o card pela posição/título.
        fresh = self.page.evaluate(self.extract)["jobs"]
        if index >= len(fresh) or fresh[index].get("title") != item["title"]:
            raise SourceProblem(
                "O card mudou antes da abertura do detalhe.", "parcial", "click_target_changed"
            )
        key = str(fresh[index].get("click", ""))
        if not key.isdecimal():
            raise SourceProblem(
                "Não foi possível identificar o controle da vaga.",
                "parcial",
                "click_target_missing",
            )
        target = self.page.locator(f'[data-rapidjob-click="{key}"]')
        if target.count() != 1:
            raise SourceProblem(
                "Controle da vaga ausente ou ambíguo.", "parcial", "click_target_missing"
            )
        touched = False
        try:
            touched = True
            target.click(timeout=self.remaining(), no_wait_after=True)
            state = {"changed": False, "dialog": False}
            stop = time.monotonic() + min(6, self.remaining() / 1000)
            popup = None
            while time.monotonic() < stop:
                opened = [p for p in self.page.context.pages if p not in before]
                if len(opened) > 1:
                    raise SourceProblem(
                        "O clique abriu várias janelas; destino ambíguo.",
                        "parcial",
                        "click_ambiguous_popup",
                    )
                popup = next(iter(opened), None)
                try:
                    state = self.page.evaluate(STATE, {"url": original, "title": item["title"]})
                except BrowserError:
                    self.page.wait_for_load_state("domcontentloaded", timeout=self.remaining())
                    continue
                if popup or state["changed"] or state["dialog"]:
                    break
                try:
                    self.page.wait_for_function(
                        f"args => {{const s=({STATE})(args);return s.changed||s.dialog;}}",
                        arg={"url": original, "title": item["title"]},
                        timeout=min(250, self.remaining()),
                    )
                except BrowserTimeout:
                    pass
            if not popup and not state["changed"] and not state["dialog"]:
                raise SourceProblem(
                    "O clique não abriu um detalhe de vaga reconhecível.",
                    "parcial",
                    "click_no_detail",
                )
            detail = popup or self.page
            if popup:
                popup.wait_for_url(
                    lambda url: urlsplit(url).scheme in {"http", "https"}, timeout=self.remaining()
                )
            detail.wait_for_load_state("domcontentloaded", timeout=self.remaining())
            url = detail.url if popup or state["changed"] else ""
            root = (
                self.page.locator('[data-rapidjob-dialog="active"]:visible').first
                if state["dialog"] and not popup
                else detail.locator("main,article,body").first
            )
            text = root.inner_text(timeout=self.remaining())
            if not url:
                # Alguns modais expõem uma URL pública própria sem mudar location.href.
                links = root.locator("a[href],[data-job-url]").evaluate_all("""elements =>
                    elements.filter(e=>! /candidat|apply|inscrev/i.test(e.textContent)).map(e=>
                    new URL(e.dataset.jobUrl || e.href, document.baseURI).href)
                    .filter(u=>u && /\\/(jobs?|vagas?|positions?)\\/.+/i.test(u))
                """)
                links = list(dict.fromkeys(links))
                if len(links) == 1:
                    url = links[0]
            if not url or url == original:
                raise SourceProblem(
                    "Detalhe aberto, mas sem URL individual compartilhável.",
                    "parcial",
                    "click_without_url",
                )
            validate_target(url)
            detail_mode = root.locator(
                '[class*="modality"],[class*="modalidade"],[class*="workplace"]'
            ).first
            mode = detail_mode.inner_text() if detail_mode.count() else ""
            structured = [
                j
                for j in detail.evaluate(self.extract)["jobs"]
                if j.get("structured")
                and (
                    str(j.get("title") or "").strip().casefold() == item["title"].casefold()
                    or j.get("url") == url
                )
            ]
            if len(structured) == 1:
                mode += " | " + structured[0].get("mode", "")
                text += "\n" + structured[0].get("text", "")
            return {
                **item,
                "url": url,
                "text": item.get("text", "") + "\n" + text,
                "detail_mode": mode,
            }
        finally:
            for popup in list(self.page.context.pages):
                if popup not in before:
                    popup.close()
            if touched:
                try:
                    self._restore(original, snapshot, step)
                except BrowserError as error:
                    raise SourceProblem(
                        "Não foi possível retornar à listagem após abrir o detalhe.",
                        "parcial",
                        "listing_restore_failed",
                    ) from error
