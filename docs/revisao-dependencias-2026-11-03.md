# Revisão manual de dependências — 03/11/2026

## Resultado e escopo

Foram revisados os diffs, destinos e checks dos 12 PRs abertos por `dependabot[bot]`, usando a API pública do GitHub. Todos apontam para develop. O PR #1 é do usuário e não faz parte desta revisão. As versões são as observadas nesta consulta; o bot pode atualizar os PRs depois.

Recomendação: não integrar os PRs individualmente. Consolidar atualizações selecionadas em um PR manual posterior, aprovado pelo usuário. Não afirmar ausência de vulnerabilidades com base apenas no rótulo de atualização do bot ou no sucesso da CI.

| PR | Alteração | CI observada | Parecer |
|---|---|---|---|
| [#2](https://github.com/Levyhb/rapid-job-search/pull/2) | PostgreSQL 17 → 18 | Aprovada | Adiar. Só muda a imagem; não migra o volume existente. Exige backup, restauração/upgrade e adaptação dos mounts. Não incluir cegamente numa atualização geral. |
| [#3](https://github.com/Levyhb/rapid-job-search/pull/3) | setup-node 4 → 7.1.0 | Aprovada | Candidato a PR manual, preservando SHA completo e versão Node do projeto. Sem necessidade funcional imediata identificada. |
| [#4](https://github.com/Levyhb/rapid-job-search/pull/4) | checkout 4 → 7.0.1 | Aprovada | Candidato a PR manual com revisão da mudança principal; manter pin por SHA. |
| [#5](https://github.com/Levyhb/rapid-job-search/pull/5) | setup-python 5 → 7.1.0 | Aprovada | Candidato a PR manual, mantendo runtime Python e SHA coerentes. |
| [#6](https://github.com/Levyhb/rapid-job-search/pull/6) | Starlette 1.9.0 → 1.10.0 | Aprovada | Atualização de parsing de formulários; candidata ao conjunto Python, validando a compatibilidade com FastAPI. |
| [#7](https://github.com/Levyhb/rapid-job-search/pull/7) | tzdata 2026.5 → 2026.6 | Aprovada | Atualiza regras de fusos; candidata a patch conjunto. A aplicação não implementa agendamento de buscas. |
| [#8](https://github.com/Levyhb/rapid-job-search/pull/8) | Ruff 0.17.2 → 0.17.3 | Aprovada | Ferramenta de desenvolvimento; candidata ao patch conjunto. |
| [#9](https://github.com/Levyhb/rapid-job-search/pull/9) | React/React DOM 19.3.0 → 19.3.1 | Aprovada | Patch conjunto das duas bibliotecas; candidato preferencial, conferindo Next.js e comportamento no navegador. Release notes citam transporte de React Server Components, sem evidência suficiente nesta revisão para classificar o PR como correção urgente de CVE. |
| [#10](https://github.com/Levyhb/rapid-job-search/pull/10) | pydantic-settings 2.16.1 → 2.16.2 | Aprovada | Correções de configurações aninhadas/CLI/secrets; candidata ao patch conjunto. |
| [#11](https://github.com/Levyhb/rapid-job-search/pull/11) | redis-py 7.4.1 → 8.1.0 | Aprovada | Adiar major. O PR amplia `redis<8` para `<9`; conferir integração real RQ/worker/Redis, além de mocks. Não atualiza o servidor Redis do Compose. |
| [#13](https://github.com/Levyhb/rapid-job-search/pull/13) | ESLint 9.39.5 → 10.14.0 | Aprovada | Adiar major para revisão conjunta de Next/ESLint/plugins. O lock proposto ainda contém minimatch 3.1.5 e 10.2.6; este PR sozinho não elimina o alerta <11.0.1 identificado abaixo. |
| [#14](https://github.com/Levyhb/rapid-job-search/pull/14) | TypeScript 5.9.3 → 7.0.2 | Frontend reprovado; demais aprovados | Não integrar como está. A migração exige investigação da falha e compatibilidade do conjunto de ferramentas. |

## Verificação de vulnerabilidades

- `npm audit --package-lock-only --json` do lock atual retornou 16 entradas moderadas e nenhuma alta/crítica, na cadeia de ferramentas ESLint/Next/TypeScript, derivadas do advisory de minimatch sobre negação de serviço por globparts amplification. São entradas de dependências/cadeias, não 16 falhas independentes da aplicação.
- O audit sugeriu downgrades principais de ESLint/configuração Next; não executar `npm audit fix --force`. Definir uma atualização compatível do conjunto no PR manual.
- Consulta OSV em lote para as 45 versões fixadas de Python retornou zero ocorrências nesta data. Não equivale a cobertura universal nem inclui Docker, sistema operacional ou Actions.
- API de alertas do repositório retornou HTTP 401 sem autenticação. Não foi possível confirmar ou descartar os alertas privados do GitHub. Antes de fechar como atualização adiável, conferir a aba Security autenticada.
- Relatórios brutos de consulta/audit estão em work, fora do Git. Nenhuma dependência foi atualizada nesta entrega.

## Desativação solicitada

Removido `.github/dependabot.yml` na branch `feature/revisao-manual-dependencias`. A exclusão só desativa o agendamento remoto depois de integrada à branch padrão do GitHub. Na interface Settings → Advanced Security (ou Code security), desativar Dependabot security updates separadamente, mantendo os alertas de segurança e o dependency graph habilitados. Retirar o agendamento de versões não desativa os PRs automáticos de segurança.

Após autenticação do Git, removido o agendamento diretamente na branch padrão `main` (commit `22d1e16`) e sincronizada a alteração com `develop`. Os 12 PRs revisados (#2–#11, #13 e #14) foram fechados sem merge; o PR #1 do usuário permanece aberto. Nenhuma dependência foi atualizada.

O GitHub confirmou `automated-security-fixes.enabled: false`. A tentativa de desativar retornou HTTP 422 informando que vulnerability alerts precisariam estar habilitados para configurar essa opção; a consulta posterior confirmou PRs automáticos de segurança desativados. Não alteramos o estado dos alertas de vulnerabilidade nem dismissamos alertas. A leitura dos alertas autenticada retornou HTTP 403, portanto a revisão não certifica ausência de alertas privados. Corrigir as ocorrências conhecidas de npm no futuro PR manual permanece pendente.

## Fontes

- [Repositório e PRs](https://github.com/Levyhb/rapid-job-search/pulls).
- [Opções do Dependabot](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference).
- [React 19.3.1](https://github.com/react/react/releases/tag/v19.3.1).
- [Starlette 1.10.0](https://github.com/Kludex/starlette/releases/tag/1.10.0).
- [Imagem oficial PostgreSQL: alterações em PGDATA e VOLUME a partir de 18](https://hub.docker.com/_/postgres).
