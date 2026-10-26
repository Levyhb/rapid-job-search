# RapidJobSearch — plano de desenvolvimento por etapas

Atualizado em 26/10/2026. Este é o roteiro de implementação do escopo atual. O plano original continua como referência de contexto; os pedidos mais recentes do usuário prevalecem sobre requisitos conflitantes.

## Objetivo da primeira versão

Cadastrar empresas (nome e URL), configurar cargos e iniciar manualmente uma busca por vagas remotas. Consultar as páginas dos portais suportados, contar progressivamente os resultados compatíveis únicos e apresentar o total final e uma tabela paginada com links diretos.

## Decisões de produto

- Nome: **RapidJobSearch**. Interface em português do Brasil.
- Duas abas principais: **Busca por vagas** (resumo, botão, progresso e resultados) e **Empresas e cargos** (cadastro/importação de empresas e seleção de cargos). A busca é a aba inicial; o processamento não é interrompido ao trocar de aba.
- Empresas persistidas em documento JSON local, com importação/exportação no mesmo formato junto do cadastro. PostgreSQL será usado para configurações de busca, execuções e vagas; não haverá dois cadastros de empresas independentes.
- Cargos são opções alternativas: basta um termo no título. Suportar variações explícitas, incluindo fullstack/full stack/full-stack, backend/back-end e frontend/front-end.
- Somente vagas com evidência de modalidade remota. Consultar detalhes quando a listagem for inconclusiva; não inferir remoto pela empresa. Preservar restrições territoriais.
- Resultados finais terão Nome da empresa | Título da vaga (link) | Remoto/Híbrido. Registrar a modalidade da fonte e sua classificação normalizada para exibição e filtros futuros; manter somente remoto no filtro atual.
- Paginação tanto na coleta dos portais quanto na tabela da aplicação.
- Contagem durante a busca = vagas compatíveis únicas já persistidas naquela execução. Falhas e duplicatas não entram no contador.
- Falhas de uma fonte vão para logs no backend e `console.log` no navegador. Não exibir erros de coleta na tela e continuar nas outras empresas. O total corresponde ao que foi encontrado; não afirmar que todos os portais foram consultados com sucesso.
- Validação de formulário e JSON inválido terá mensagem junto ao campo/importação: a regra de erros silenciosos se refere à coleta dos portais.
- Sem login, candidatura automática, IA, currículo, alertas, agendamento ou múltiplos usuários nesta versão. Favoritos, perfis avançados e comparação histórica ficam para evoluções posteriores.

## Como executar cada etapa

1. Partir da `develop` atualizada e abrir uma branch `feature/*` da etapa.
2. Implementar somente os entregáveis descritos, incluindo a integração frontend/backend necessária.
3. Executar os critérios de aceite e checks apropriados à mudança.
4. Registrar o que foi entregue, limitações e evidências neste plano ou na documentação da etapa.
5. Fazer commit e integrar em `develop` quando concluída. Usar pull request quando o GitHub estiver configurado.

Não avançar declarando uma etapa pronta se os critérios não foram atendidos. Esta divisão não exige nova aprovação a cada arquivo ou decisão técnica rotineira. As próximas etapas serão desenvolvidas conforme solicitadas.

## Visão geral

| Etapa | Entrega | Dependências | Situação |
|---|---|---|---|
| 0 | Gitflow e ambiente local | — | Concluída |
| 1 | Identidade, layout base e CSS global | 0 | Concluída |
| 2 | Cadastro de empresas com persistência JSON | 1 | Concluída |
| 3 | Importação/exportação de empresas | 2 | Concluída |
| 4 | Cargos e regras de vagas remotas | 1, 0 | Concluída |
| 5 | Validar fontes e coletar um portal inteiro | 2, 4 | Concluída: Alice, Afya e Arco |
| 6 | Pesquisa em segundo plano e progresso | 5 | Concluída |
| 7 | Resultados paginados e total final | 6 | Concluída |
| 8 | Expandir fontes e consolidar falhas | 7 | Em andamento: validação automática e logs estruturados entregues |
| 9 | Validação integrada e primeira release | 8 | Pendente |

## Etapa 0 — ambiente local

**Entregue:** Next.js/TypeScript/Tailwind, FastAPI, PostgreSQL, Alembic, Redis, RQ, Playwright/Chromium e scripts PowerShell. Branches `main`/`develop`, setup integrado em `develop`.

**Aceite realizado:** testes da API, build, lint, TypeScript, conexão com os serviços, navegação desktop/mobile e tarefa de verificação no worker Linux. Evidências em `docs/validacao-ambiente.md`.

## Etapa 1 — identidade e layout base

**Branch:** `feature/plano-layout`.

**Frontend:** aplicar RapidJobSearch na identidade e nos metadados. Organizar painel em Busca por vagas e Empresas e cargos; reservar resumo, pesquisa e tabela na aba inicial. Identificar a prévia e manter ações ainda não implementadas desabilitadas.

**CSS global:** centralizar cores, tipografia, espaçamento, bordas, sombras, botões, campos, cards, tabela, estados de foco, responsividade e redução de movimento em `frontend/src/app/globals.css`. Reutilizar classes/componentes nas etapas seguintes.

**Aceite:** navegação por âncoras funcional, foco visível, layout sem overflow da página em celular, metadados corretos e nenhuma vaga ou contagem fictícia. Diagnóstico técnico separado da experiência principal.

**Verificado nesta entrega:** lint, TypeScript, build e cinco testes da API passaram. Inspeção visual desktop/mobile e smoke test no Chromium confirmaram marca, navegação, diagnóstico conectado aos três serviços, ações pendentes desabilitadas e ausência de overflow em larguras de 320, 390, 768 e 1024 px. Não houve erro JavaScript. Cadastro/pesquisa continuam pendentes conforme o roteiro.

## Etapa 2 — cadastrar empresas

**Branch entregue:** `feature/cadastro-empresas`. Cadastro, edição, remoção, filtro, lista fixa com rolagem e toasts implementados; detalhes em `docs/cadastro-empresas.md`.

**Backend:** definir schema versionado; criar serviço de leitura/escrita de `backend/data/empresas.json` (caminho configurável, arquivo real fora do Git). Gravação atômica e coordenação de escritas concorrentes para impedir perda de dados. Arquivo ausente inicia catálogo vazio; arquivo corrompido não pode ser substituído silenciosamente.

**API proposta:** `GET/POST /api/companies`, `PATCH/DELETE /api/companies/{id}`. Identidade interna estável; impedir duplicatas pela combinação de nome e URL normalizados, preservando URLs necessárias ao portal.

**Frontend:** formulário Nome/URL, listagem, edição e remoção. Campo/estado vazio orienta a primeira inclusão. Confirmar alterações somente após persistência.

**Aceite:** cadastrar, editar, remover, reiniciar API e reencontrar os dados. Validar URL, campos obrigatórios, duplicatas e concorrência. Alterar o catálogo durante uma busca não muda a cópia usada pela execução em andamento.

## Etapa 3 — importar/exportar JSON

**Branch entregue:** `feature/cadastro-empresas`. Arquivo/texto JSON com prévia e exportação em modal com cópia formatada implementados; detalhes em `docs/cadastro-empresas.md`.

**Contrato compartilhável mínimo:**

```json
{
  "versao": 1,
  "empresas": [
    { "nome": "Empresa A", "url": "https://empresa-a.com/carreiras" }
  ]
}
```

**Backend:** validar estrutura, versão, URLs, tamanho e duplicatas. Separar prévia da confirmação. IDs internos são opcionais no intercâmbio; arquivo compartilhado não precisa de informações locais.

**Frontend:** botões Importar JSON/Exportar JSON ao lado do cadastro. Mostrar prévia das linhas válidas e inválidas, permitir importar apenas válidas e mesclar por padrão. Substituição completa exige ação explícita de confirmação. Exportar como arquivo `.json` utilizável por outra instalação.

**Aceite:** exportar → importar em catálogo vazio → obter a mesma lista. Arquivo inválido não altera o cadastro; duplicatas não se multiplicam; cancelamento preserva os dados.

## Etapa 4 — cargos e filtro remoto

**Branch:** `feature/cargos-filtros`. Entregue: CRUD, seleção, variações explícitas, prévia no backend e regras de correspondência/modalidade. Evidências em `docs/cargos-e-execucao.md`.

**Backend:** persistir cargos no PostgreSQL com migração. Implementar regra de alternativas no título, normalização de caixa/acentos/separadores e limites de palavras. Variações aceitas precisam estar documentadas e visíveis. Não usar a descrição para satisfazer o cargo por padrão.

**Frontend:** adicionar/remover cargos em chips, apresentar variações e a regra “qualquer um dos termos no título”. Mostrar “Somente vagas remotas” como regra fixa da primeira versão.

**Aceite:** Full-Stack Developer corresponde a fullstack com a variação cadastrada; Backend Developer corresponde a backend; Analista de Suporte com backend apenas na descrição não corresponde. Remota inclui; presencial/híbrida exclui; modalidade desconhecida exige detalhes e, sem confirmação, exclui. Cargos sobrevivem ao reinício.

## Etapa 5 — validar fontes e entregar um coletor

**Branch:** `feature/primeiro-coletor`.

**Entrada recebida:** Alice, Afya e Arco. As fontes foram verificadas e os coletores entregues; ver `docs/coleta-portais.md`. Para novas integrações, será necessária outra amostra real. Novos portais só serão classificados como validados após consulta real e conferência de cobertura.

**Backend:** criar contrato comum de vaga e de cobertura. Preferir dados públicos estruturados confiáveis; usar Playwright quando necessário. Percorrer todas as páginas/lotes, buscar detalhes dos candidatos, extrair modalidade e URL direta, limitar tentativas/duração e detectar loops. Aplicar regras da etapa 4.

**Modalidade preservada para as próximas etapas:** cada anúncio deve distinguir remoto, híbrido, presencial e desconhecido, guardando também o rótulo/evidência da fonte. Nunca preencher desconhecido como remoto. A modalidade não participa do match de cargo: após o título corresponder, aplicar separadamente o filtro somente remoto. Um controle futuro poderá incluir híbridas, mas ainda não faz parte da busca atual.

**Identidade:** usar ID da fonte quando disponível; senão URL conservadoramente normalizada. Título sozinho não identifica uma vaga.

**Aceite:** encontrar vaga remota compatível além da primeira página; confirmar término da paginação; preservar resultados quando uma página posterior falhar. Limite atingido registra coleta parcial no diagnóstico interno. Testar com cenário controlado e conferir amostras reais, inclusive descartes.

## Etapa 6 — botão de pesquisa e progresso

**Branch:** `feature/execucao-progresso`.

**Backend:** criar migrações para execuções, consultas por empresa, vagas e associações com a execução. `POST /api/searches` salva configuração imutável e retorna ID com HTTP 202. RQ executa consultas em segundo plano; coordenar buscas ao mesmo portal e tornar repetição idempotente. Salvar resultados antes de atualizar a contagem.

**API de acompanhamento:** `GET /api/searches/{id}` retorna estado e contagem compatível única. `GET /api/searches/{id}/diagnostics` entrega falhas incrementais para o console, com identificadores que evitam logs repetidos no polling. A resposta nunca inclui credenciais ou informações desnecessárias.

**Frontend:** botão Realizar pesquisa, loading e “Encontramos N vagas até agora”. Polling com intervalo limitado e cancelamento ao desmontar; retomar acompanhamento ao voltar para a tela. Não mostrar porcentagem se o total for desconhecido. Botão indisponível sem empresas/termos ou enquanto a execução já estiver ativa.

**Aceite:** contagem aumenta à medida que resultados reais são persistidos; navegar ou recarregar não cancela a tarefa. Falha de uma empresa não impede outra; reinício marca execuções interrompidas de forma verdadeira. Erros de coleta aparecem somente nos logs/console. Não declarar uma execução em andamento como finalizada por uma falha temporária do polling.

## Etapa 7 — total final e resultados paginados

**Branch:** `feature/resultados-paginados`.

**Backend:** `GET /api/searches/{id}/jobs?page=1&page_size=20`, com total e ordenação estável. Consultar apenas as vagas associadas à execução escolhida. Uma vaga encontrada por vários termos não vira múltiplas linhas.

**Frontend:** ao terminar, exibir “Pesquisa finalizada: N vagas encontradas” e tabela Nome da empresa | Título da vaga (link) | Remoto/Híbrido. Título clicável abre outra aba; a terceira coluna apresenta a modalidade confirmada pela fonte. Enquanto o filtro for somente remoto, vagas híbridas continuam excluídas. Paginação com anterior/próxima, página atual e total; preservar contexto durante o carregamento e usar indicação de carregamento nos resultados.

**Aceite:** total final corresponde à quantidade única persistida; páginas não omitem nem repetem linhas; cada título abre seu anúncio; zero resultados tem estado vazio; falhas de portais não aparecem na tabela nem no total. Texto não promete cobertura completa das fontes.

## Etapa 8 — cobertura e falhas

**Branch:** `feature/cobertura-portais`.

**Backend:** adicionar outros portais priorizados a partir da lista real. Reutilizar fornecedores quando validado. Diferenciar falta de resultados, bloqueio, formato não suportado, falha de leitura e coleta parcial nos logs. Capturar empresa, URL, execução, etapa e motivo. Manter falhas de coleta fora da interface e do contador.

**Aceite:** consultar fontes independentes, manter resultados válidos com falhas parciais e não prometer suporte universal. Não superar login/desafios de acesso automaticamente. Atualizar matriz de fontes suportadas.

## Etapa 9 — primeira versão utilizável

**Branch:** `release/0.1.0` após integrar as features em `develop`.

**Entregáveis:** instruções locais atualizadas, dados JSON de exemplo claramente identificados, matriz de suporte, checks automatizados e documentação de limitações. Quando o GitHub estiver configurado, adicionar CI para lint/testes/build.

**Aceite integrado:** importar empresas reais, definir termos, buscar, acompanhar a contagem e abrir uma vaga remota da tabela. Reiniciar sem perder cadastro/configuração/resultados. Testar duplicatas, paginação, JSON inválido, falha isolada, todos os portais falhando, interrupção e viewport móvel.

Após validação, integrar release em `main` e `develop` e criar tag `v0.1.0`. Publicar no GitHub quando solicitado/configurado.

## Direção de layout

- Painel claro, fundo suave e cards brancos; cor principal índigo, verde para modalidade remota/conexão e texto de alto contraste.
- Cabeçalho com marca e abas Busca por vagas e Empresas e cargos.
- Abertura curta com objetivo da ferramenta e ação para começar a configurar.
- Empresas e cargos na aba de configuração, com atalho para voltar à busca.
- Aba de busca com quantidades de empresas cadastradas/cargos selecionados, botão, loading/contador e resultados logo abaixo. Antes da primeira consulta, preservar o estado vazio de Vagas encontradas.
- Tabela com foco no nome da empresa e título da vaga, sem informações técnicas no fluxo de pesquisa.
- Controles com labels, foco visível, estados disabled/loading, teclado e suporte a telas pequenas.
- Modais de cadastro/edição de empresas e cargos com altura mínima de 620px no desktop, limitada à altura disponível; no mobile, tela cheia com rolagem interna e cabeçalho fixo no modal.
- Importação/exportação JSON em modal amplo (até 900 × 800px), tela cheia no mobile, cabeçalho e ações fixos, editor legível, revisão antes de salvar e exportação por cópia ou download do arquivo formatado.
- Diagnóstico de desenvolvimento em área recolhível, separado do painel de oportunidades.

## Próxima etapa funcional

**Etapa 8: ampliar a cobertura conforme novas empresas forem priorizadas.** As etapas 5–7 foram entregues com as fontes Alice/InHire, Afya/Gupy e Arco/Greenhouse, execução RQ e resultados paginados. Evidências e limites em `docs/coleta-portais.md`.

Atualização de suporte: validação assíncrona ao cadastrar/editar URL e rótulos Compatível/Precisa de adaptação/Acesso bloqueado nas respostas e logs. Rede sem confirmação fica inconclusiva. Indicador de exclamação, contagem de erros e modal serão uma melhoria futura. Detalhes em `docs/validacao-suporte-portais.md`.
