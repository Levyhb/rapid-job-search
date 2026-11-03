# Coleta de páginas com Playwright

O worker tenta primeiro os coletores HTTPX de InHire, Gupy e Greenhouse. Quando
eles retornam `nao_suportada`, o coletor abre Chromium com Playwright para ler
o HTML após a execução do JavaScript. Bloqueios, desafios de acesso e falhas de
rede não provocam uma nova tentativa pelo navegador.

## Navegação e extração

O extrator lê `JobPosting` em JSON-LD e cards/links de anúncios. Reconhece também
links de vagas dentro de painéis recolhidos de acordeões, desde que estejam
associados ao título visível por `aria-controls`. Preserva título, URL,
modalidade original e localidade quando identificada na fonte.

Após cada listagem, procura um controle inequívoco de próxima página ou carregar
mais, em português ou inglês. Sem esse controle, tenta rolar a página e espera
novos anúncios. Repetições, controles ambíguos e paginação sem alteração geram
diagnóstico parcial. A espera observa mudanças no DOM; não utiliza pausas fixas.

Os cargos e suas variações são comparados **somente com o título**, usando as
regras existentes de acentos, caixa, palavras completas e flexões de
desenvolvedor/desenvolvedora. A descrição serve para confirmar modalidade,
sem satisfazer o filtro de cargo. Somente vagas remotas confirmadas são salvas.
Mencionar auxílio home office nos benefícios não confirma trabalho remoto.
Evidências contraditórias deixam a modalidade desconhecida e excluem a vaga.

Detalhes são abertos para títulos compatíveis cuja modalidade ainda seja
desconhecida ou cujo card não exponha uma URL. Cards sem href com modalidade
explicitamente híbrida/presencial não são abertos. A coleta não preenche inputs: um campo genérico pode
pesquisar conteúdo institucional, e depender da busca do portal pode esconder
variações de cargo.

## Desempenho e limites

- Até duas empresas simultâneas, com uma sessão HTTP e um Chromium por thread.
  O navegador é iniciado somente se necessário e reutilizado entre empresas;
  cada empresa tem um contexto isolado e o armazenamento de cookies HTTP é limpo.
- A comunicação com o banco ocorre exclusivamente na thread principal do worker.
  Vagas e progresso são persistidos conforme chegam, mantendo o acompanhamento
  e a paginação existentes na interface.
- Orçamento de navegação de 120 segundos por empresa, até 30 listagens,
  50 páginas de detalhes e 400 requisições interceptadas de conteúdo. As chamadas
  individuais respeitam o tempo restante. O HTTP inicial mantém seu orçamento
  separado de 180 segundos. Os limites encerram a coleta com diagnóstico parcial.
- Imagens, fontes, mídia e hosts conhecidos de Google Analytics/Tag Manager/
  DoubleClick são descartados. Seu descarte intencional não é uma falha de vaga.
- Relatórios incluem `duration_seconds` (HTTP + navegador), `batches`, `examined`,
  `expected`, `details_opened`, `resolved_jobs`, `click_failures` e `requests`.
  Esta última conta as requisições de
  conteúdo interceptadas no navegador, não o total de chamadas dos adaptadores HTTP.

Uma listagem genérica só é declarada concluída quando há um estado vazio
explícito ou um total explícito reconhecido que confere com os anúncios únicos
examinados, sem outras falhas. Sem essa evidência, as vagas já confirmadas são
preservadas e a fonte recebe `Precisa de adaptação` por cobertura não confirmada.
Quantidade de anúncios examinados é diferente de quantidade de vagas que
passaram pelos filtros.

## Rede e limitações

As requisições GET são atendidas pelo transporte público HTTPX existente, com
validação de DNS/IP, TLS, redirects, tamanho de resposta e prazo. Chromium usa
um proxy sem saída como proteção adicional; não há acesso direto alternativo.
Service workers, WebSockets, WebTransport e downloads são bloqueados. URLs de
navegação controlada são resolvidas antes de `goto`, preservando links relativos
sem entregar redirects ao navegador. Redirecionamentos de navegação disparados
por scripts que não passam por esse fluxo são bloqueados e exigem adaptação.

O extrator percorre Shadow DOM aberto. POST e outros métodos são bloqueados. Não há coletores específicos por
empresa. Se a listagem depender de métodos não suportados, login,
CAPTCHA, iframe de vagas, filtros obrigatórios, shadow DOM fechado ou de um
layout não reconhecido, um adaptador específico pode ser necessário. Esta
implementação não promete suporte a qualquer site. Não clica em candidaturas
nem tenta contornar controles de acesso.

## Execução e diagnóstico

O Dockerfile já instala Chromium. Após atualizar o código montado no contêiner:

```powershell
docker compose restart worker
docker compose logs --tail 100 worker
```

Se a imagem ainda não existir ou as dependências tiverem mudado:

```powershell
docker compose --profile worker up -d --build worker
```

A API permanece iniciada por `py run`; a pesquisa utiliza o worker. Cadastre
empresas e cargos na interface e inicie uma nova busca para usar o coletor.
Falhas de acesso ou de reconhecimento da listagem aparecem nos diagnósticos utilizados pelo modal **Saber mais**. Coletas parciais com anúncios examinados ficam como avisos técnicos em `source_validations` e nos logs, sem entrar no contador de sites com falhas. Zero vagas compatíveis com os cargos também não significa falha.

Para executar os testes locais na raiz, após o setup:

```powershell
.\backend\.venv\Scripts\python.exe -m playwright install chromium
.\backend\.venv\Scripts\python.exe -m pytest backend\tests
.\backend\.venv\Scripts\python.exe -m ruff check backend
```

Os testes de navegador usam HTML e respostas HTTP controlados, sem depender
de mudanças em sites reais. A CI instala Chromium antes de executar essa suíte.
As APIs utilizadas estão descritas na [documentação de rede do Playwright](https://playwright.dev/python/docs/network).


## Cards sem link e leitura de detalhes

Quando um card não possui `href`, o coletor procura um título ou controle de
“Ver vaga”, “Acessar vaga”, “Ver detalhes” ou equivalente em inglês. Abre apenas
cargos compatíveis e evita cards explicitamente híbridos/presenciais.

O clique pode abrir detalhes na mesma aba, em uma nova aba ou em modal. A URL
individual é validada e preserva hashes que identifiquem a vaga. Em modais sem
mudança de endereço, o coletor procura um link público próprio. Sem URL
compartilhável, registra `click_without_url`, sem inventar um endereço.

Ao terminar, fecha a aba/modal ou volta à listagem. Confere os cards e, se o
site tiver perdido a paginação, reproduz os avanços para retornar ao mesmo ponto.
Falha ao restaurar encerra a fonte como parcial com `listing_restore_failed`.
Páginas já lidas e URLs repetidas não geram vagas duplicadas.

## Títulos, tabelas e animações

O título é extraído de um campo próprio, incluindo nomes de classe em português
como `titulo`. Textos de botões ou links de candidatura não são incorporados
ao cargo. Um link de detalhes pode conter um CTA combinado sem que a aplicação
preencha ou envie o formulário de candidatura. Bancos de talentos são contados
na cobertura da listagem, mas não são emitidos como oportunidades.

Em tabelas, cada linha fornece título/link e campos de modalidade/localidade.
Uma célula com modalidade explícita é considerada separadamente de benefícios
e descrições institucionais.

Conteúdo já carregado que esteja oculto somente por animações identificadas
pode ser lido sem forçar cliques ou alterar estilos. Elementos filtrados com
`hidden`, `display:none` ou `aria-hidden` continuam sendo respeitados. O extrator
percorre Shadow DOM aberto; layouts não reconhecidos ficam no diagnóstico.

## Falhas, avisos e cobertura

`has_failure` controla a presença no contador e no modal de falhas;
`has_warning` identifica uma coleta parcial que conseguiu ler anúncios.
As flags são recalculadas inclusive para relatórios antigos, preservando
os registros históricos. O frontend também reconhece o formato anterior.

| Situação | Contador de falhas |
|---|---|
| Leitura concluída, inclusive zero vagas compatíveis | Não entra |
| Estado vazio explícito reconhecido | Não entra |
| Cobertura parcial com anúncios examinados | Aviso técnico nos logs |
| Falha de acesso, bloqueio ou listagem não reconhecida | Entra |
| Coleta parcial sem anúncios examinados | Entra |
| Falhas de clique sem nenhuma URL de vaga confirmada | Entra |

Se uma fonte anunciar mais vagas do que os links únicos disponíveis, o coletor
registra `incomplete_coverage` e mantém os resultados confirmados. O total final
representa somente vagas remotas compatíveis efetivamente persistidas; não
promete cobertura completa de fontes arbitrárias.

## Critérios de verificação

A suíte usa empresas fictícias e respostas controladas para testar listagem
dinâmica, paginação, carregar mais, rolagem, links, cliques, abas, modais,
restauração, duplicatas, modalidade e restrições de rede. As verificações reais
de um portal devem conferir título, URL, modalidade, quantidade e diagnóstico;
dados de inspeções específicas são mantidos apenas em arquivos locais ignorados.

O comportamento é compartilhado entre empresas. Coletores HTTP por plataforma
usam os identificadores presentes nas URLs cadastradas; o fallback Playwright
procura estruturas de anúncios sem regras por nome ou domínio de empregador.
