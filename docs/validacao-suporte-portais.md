# Identificação e validação de suporte dos portais

Implementado em 26/10/2026.

## Escopo entregue

- Identificar InHire e Gupy pelo domínio, Greenhouse pelo domínio ou embed, incluindo redirecionamentos HTTP para plataformas conhecidas.
- Ao cadastrar ou editar uma empresa pela API/tela, salvar o cadastro primeiro e agendar a validação no worker RQ. A requisição não espera a coleta remota terminar.
- Validar a leitura usando o coletor real e sua cobertura. Reconhecer apenas o domínio não torna um site compatível automaticamente.
- Em cada busca, produzir uma nova validação por fonte, persistida no relatório da execução, e enviá-la no acompanhamento.
- Registrar os rótulos nos logs e apresentar falhas de consulta no contador/modal da busca.

## Rótulos

| Rótulo | `support_status` | Quando é emitido |
|---|---|---|
| Compatível | `compatible` | Listagem reconhecida e completamente processada; pode haver zero vagas |
| Precisa de adaptação | `needs_adaptation` | Formato não suportado, falha de interpretação ou cobertura parcial |
| Acesso bloqueado | `access_blocked` | HTTP 401/403/429, desafio de acesso ou login exigido |
| Validação inconclusiva | `null` | Rede indisponível, timeout ou infraestrutura de validação sem confirmação |

Uma falha de rede não prova incompatibilidade. Os estados de ciclo de vida são `pending`, `completed`, `inconclusive` ou `not_checked` quando ainda não houve validação. Compatibilidade descreve a leitura observada naquele momento; não promete encontrar cargos compatíveis nem disponibilidade permanente da fonte.

Desafios de acesso HTTP 200 são reconhecidos por sinais específicos de página de desafio (título/formulário/cabeçalho). Um link normal de login ou a presença de um formulário de candidatura não basta para classificar toda a listagem como bloqueada. A ferramenta não tenta contornar desafios ou autenticação.

## Formato dos logs e dos dados

Exemplo de log:

```text
[RapidJobSearch] [Precisa de adaptação] Empresa X | https://empresa.com/carreiras | unknown | Portal sem formato público reconhecido ou com integração ambígua.
```

Cada registro inclui `company_id`, `company`, `url`, `resolved_url`, `platform`, `support_status`, `label`, `validation_state`, `collection_status`, `code`, `message`, `checked_at` e cobertura (`examined`, `expected`, `batches`). Os códigos distinguem, por exemplo, `access_challenge`, `login_required`, `http_403`, `network_error`, `unsupported_portal`, `incomplete_coverage` e `validation_unavailable`.

- `GET /api/searches/{id}` inclui `source_validations` para todas as fontes terminadas, inclusive compatíveis.
- `diagnostics` e `GET /api/searches/{id}/diagnostics` contêm apenas falhas de consulta (`has_failure=true`). Coletas parciais com anúncios examinados permanecem em `source_validations` como avisos (`has_warning=true`), sem entrar no contador/modal de falhas. A classificação é recalculada para relatórios antigos.
- O total `found_count` continua contando somente vagas compatíveis persistidas. Classificações e falhas nunca viram vagas nem alteram artificialmente esse total.
- O frontend identifica cada evento por ID e não repete o mesmo log a cada polling/troca de aba.
- Execuções antigas sem data de validação por fonte retornam `checked_at: null`, sem inventar uma data de conferência.

O modal **Saber mais** utiliza esses registros para listar as fontes cuja consulta falhou e os respectivos motivos.

## Validação no cadastro

A migração `20261026_03` cria `portal_validations` no PostgreSQL. O cadastro de empresas e seu JSON exportável continuam no mesmo formato, sem informações técnicas adicionadas ao arquivo compartilhado.

- Criar/editar empresa agenda a tarefa `validate_portal_job` na fila `searches`.
- Banco/Redis indisponíveis não desfazem o cadastro JSON nem fazem uma operação já salva parecer um erro de salvamento; a falha de validação fica nos logs e, quando possível, como inconclusiva no banco.
- Sem worker ativo, a tarefa permanece pendente até o processamento.
- Uma URL editada recebe nova versão de validação. Resultados da URL anterior são descartados, inclusive se o trabalho antigo terminar depois.
- Remover uma empresa limpa sua validação; tarefas antigas deixam de atualizar o cadastro.
- Importações em lote preservam o comportamento atual: fontes importadas são verificadas na busca; não se agenda automaticamente uma varredura de milhares de URLs ao importar.
- O diagnóstico de uma busca permanece associado à configuração daquela execução, mesmo que a empresa seja editada depois.

Endpoints adicionais:

```text
POST /api/companies/{id}/validate     # solicitar/repetir validação
GET  /api/companies/{id}/validation   # consultar a última validação de cadastro
```

O endpoint de cadastro continua retornando a empresa. Os endpoints acima não são usados para exibir novos alertas na interface nesta entrega.

## Executar

Os comandos existentes permanecem: iniciar infraestrutura, API, frontend e worker. O script da API aplica a migração; após atualizar o código, reiniciar o worker:

```powershell
.\scripts\dev.ps1 infra
.\scripts\dev.ps1 api
# Outro terminal:
.\scripts\dev.ps1 frontend
# Outro terminal:
.\scripts\dev.ps1 worker
```

Se o worker já estiver em segundo plano: `docker compose restart worker`.

## Verificação e navegação

Os testes usam empresas fictícias e respostas controladas para validar detecção
de plataforma, hosts semelhantes, redirects, embeds, bloqueios, login, falhas
de rede, estado vazio, edição/remoção e indisponibilidade da fila. Testes do
worker verificam persistência, resultados e diagnósticos isolados por fonte.

O Playwright é o fallback genérico para fontes sem formato HTTP reconhecido.
Os limites de renderização, cliques e paginação estão em
[Coleta com Playwright](coleta-playwright.md).

## Interface de falhas

Ao concluir a pesquisa, o frontend apresenta um aviso com exclamação,
quantidade de sites com falha e **Saber mais**, ao lado do total de vagas.
O modal possui cabeçalho, botão de fechar e conteúdo com rolagem; lista empresa,
URL e motivo da falha.

A interface utiliza `has_failure` dos diagnósticos. Coletas parciais com anúncios
examinados ficam como avisos técnicos, exceto quando todas as aberturas por
clique falharam e nenhuma URL individual foi confirmada. Leitura concluída com
zero vagas permanece sucesso. Falhas não são somadas ao total de resultados.
