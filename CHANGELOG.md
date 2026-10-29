# Histórico de alterações

## Não lançado

- Aviso de sites com falha ao concluir a busca, ao lado do total de vagas, com modal de empresas, URLs e motivos; layout responsivo e rolagem interna.

## 1.0.0 — 28/10/2026

Primeira versão do RapidJobSearch publicada em `main`.

### Funcionalidades

- Painel responsivo com abas de busca e configuração de empresas/cargos.
- Cadastro, edição e remoção de empresas, inclusão em lote, filtro e importação/exportação JSON.
- Cadastro e seleção de cargos com variações explícitas, normalização de acentos/separadores e correspondência no título, incluindo Desenvolvedor/Desenvolvedora.
- Coleta de portais Gupy, InHire e Greenhouse, com validação de suporte e logs estruturados por empresa.
- Busca em segundo plano com Redis/RQ, contador progressivo e persistência no PostgreSQL.
- Resultados remotos paginados com links, modalidade e filtros por texto, empresa, cargo e nível.
- Ambiente local com Docker Compose, scripts PowerShell, migrações Alembic e atalho `py run` para a API.
- CI com testes, lint, geração de tipos, TypeScript, build, migrações e validação do Compose.

### Limitações conhecidas

- Uso pessoal, sem autenticação ou isolamento entre usuários; publicação do código não inclui hospedagem.
- A pesquisa inclui somente vagas com modalidade remota confirmada. Híbridas e presenciais ainda não entram no resultado.
- Sites próprios e plataformas não suportadas precisam de adaptadores; bloqueios ou mudanças nos portais podem limitar a coleta.
- API, PostgreSQL, Redis e worker precisam estar disponíveis para executar as buscas.
- A validação manual completa dos cenários da etapa 9 permanece no roteiro; esta release consolida as funcionalidades existentes.

### Continuidade

Tag `v1.0.0`. `main` e `develop` são sincronizadas após a integração da release; novas funcionalidades partem de `develop` conforme `docs/gitflow.md`.
