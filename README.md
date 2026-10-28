# RapidJobSearch

Painel pessoal para buscar vagas remotas nos portais das empresas cadastradas.

## Estado atual

Ambiente de desenvolvimento e layout base do RapidJobSearch implementados, com CSS global e painel responsivo. O diagnóstico recolhível verifica a conexão real com a API, PostgreSQL e Redis. Cadastro de empresas com persistência JSON no servidor, filtro, edição/remoção, importação revisada e exportação em modal com cópia formatada já funcionam. Cadastro de cargos, seleção, variações e prévia de títulos também funcionam, com persistência no PostgreSQL. A coleta de portais Gupy, InHire e Greenhouse está integrada ao botão de busca, com processamento em segundo plano, contagem e resultados remotos persistidos. Os resultados têm filtros avançados por texto, empresa, cargo e nível. Sites próprios e outras plataformas podem precisar de adaptação; não há suporte universal a qualquer URL.

O painel tem duas abas: Busca por vagas e Empresas e cargos. O roteiro de trabalho está em [docs/plano-desenvolvimento.md](docs/plano-desenvolvimento.md). Etapas 0–7 concluídas; próxima entrega: ampliar cobertura e consolidar a primeira release. O contrato e os estados da pesquisa preparados no frontend estão descritos em [docs/abas-e-pesquisa.md](docs/abas-e-pesquisa.md); o endpoint de resumo já informa o total real de empresas. Veja também [docs/cadastro-empresas.md](docs/cadastro-empresas.md).

## Publicação no GitHub

O repositório inclui CI para lint, testes, migrações, TypeScript, build e validação do Docker Compose. Consulte o [passo a passo de publicação](docs/publicacao-github.md) para configurar o remoto e enviar `main` e `develop`. Os arquivos `.env` e dados pessoais locais não são versionados. A publicação do código é independente de hospedar a aplicação.

## Stack

- Frontend: Next.js 16, React, TypeScript e Tailwind CSS.
- Backend: Python 3.14, FastAPI e Uvicorn.
- Persistência: PostgreSQL, SQLAlchemy e Alembic.
- Coleta: Playwright para Python com Chromium instalado.
- Execução em segundo plano: RQ e Redis; worker Linux via Docker.

## Pré-requisitos

- Windows com PowerShell, Git, Node.js 24 e npm.
- Python 3.14 acessível pelo launcher `py`.
- Docker Desktop iniciado e usando contêineres Linux.

As versões resolvidas estão em `frontend/package-lock.json` e `backend/requirements.lock`. O lock Python inclui ferramentas de desenvolvimento; o contêiner também é um ambiente de desenvolvimento.

## Preparar o ambiente

Na raiz do projeto:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
```

O setup cria os arquivos locais de configuração se não existirem, instala dependências, prepara Chromium, inicia PostgreSQL/Redis e executa migrações. Não é necessário ativar o ambiente virtual. O Alembic aplica as migrações de cargos, execuções de busca, vagas e validação dos portais. Uma instalação nova começa sem o catálogo pessoal de empresas, cargos e resultados.

## Executar

Atalho para iniciar apenas o backend, usando o ambiente virtual e aplicando migrações:

```powershell
cd backend
py run
```

Também funciona com `py run.py`. A API abre em `http://127.0.0.1:8000`; `Ctrl+C` encerra.
Para outra porta: `py run --port 8001`. PostgreSQL e Redis precisam estar iniciados. O worker deve rodar em outro terminal para processar buscas e validações de portais.

Com Docker Desktop aberto, execute `.\scripts\dev.ps1 infra`. Depois use terminais separados na raiz do projeto:

```powershell
# Terminal 1: API (aplica migrações e inicia com recarregamento automático)
.\scripts\dev.ps1 api

# Terminal 2: frontend com recarregamento automático
.\scripts\dev.ps1 frontend

# Terminal 3: worker Linux (necessário para as buscas e validações de portais)
.\scripts\dev.ps1 worker
```

Se a política local impedir os scripts, use `powershell -ExecutionPolicy Bypass -File scripts/dev.ps1 api`, substituindo o serviço conforme necessário.

- Frontend: http://127.0.0.1:3000
- Documentação da API: http://127.0.0.1:8000/docs
- Saúde da API: http://127.0.0.1:8000/health
- Disponibilidade de banco e Redis: http://127.0.0.1:8000/health/ready
- PostgreSQL: `127.0.0.1:55432`, banco/usuário `busca_vagas`.
- Redis: `127.0.0.1:6379`.

A porta 55432 evita conflito com o PostgreSQL já existente na máquina. As credenciais de desenvolvimento estão no Compose e no `.env.example` e servem apenas ao ambiente local. Os serviços são publicados somente na interface de loopback.

## Primeira busca

1. Abra a aba **Empresas e cargos** e cadastre empresas ou importe um JSON. Para começar, use [docs/empresas-primeira-coleta.json](docs/empresas-primeira-coleta.json); [docs/empresas-modelo.json](docs/empresas-modelo.json) demonstra o formato.
2. Cadastre e selecione os cargos e suas variações. A correspondência usa o título da vaga e o filtro atual inclui apenas vagas remotas confirmadas.
3. Com API, frontend, PostgreSQL, Redis e worker ativos, abra **Busca por vagas** e inicie a pesquisa.
4. Acompanhe o contador e consulte os resultados paginados e filtros avançados. Falhas de portais são registradas nos logs e no console do navegador.

## Configuração

- `backend/.env`: conexão com banco, Redis e origens CORS.
- `frontend/.env.local`: `NEXT_PUBLIC_API_URL`, endereço público local da API.
- Os arquivos `.env` reais não são versionados. Reinicie os processos após alterar configurações.
- Variáveis de ambiente do processo têm precedência sobre os arquivos locais.

## Verificar

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check.ps1
```

Executa Ruff, testes da API, ESLint, TypeScript, build do Next.js e validação do Compose. Os testes unitários de disponibilidade simulam falhas; o endpoint `/health/ready` verifica os serviços reais.

## Migrações

Dentro de `backend/`:

```powershell
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "descricao"
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Ao adicionar modelos, importe-os em `app/models/__init__.py` e importe esse módulo em `migrations/env.py` para registrar os metadados antes da geração.

## Serviços e encerramento

`Ctrl+C` encerra a API ou o frontend no terminal correspondente. Para iniciar somente a infraestrutura, execute `.\scripts\dev.ps1 infra`. Para parar os contêineres preservando os dados:

```powershell
docker compose --profile worker stop
```

O worker executa as tarefas reais de busca e deve permanecer ativo enquanto houver pesquisas. Alterações no código montado do worker exigem reiniciá-lo. A execução nativa alternativa `python -m app.workers.main` usa SimpleWorker no Windows, com limitações de isolamento; prefira o contêiner Linux para as coletas.

## Organização e Gitflow

- `frontend/src/app`: interface.
- `backend/app/api`: endpoints.
- `backend/app/core`: configuração e banco.
- `backend/app/collectors`, `filters`, `services`, `workers`: coleta, correspondência de cargos, persistência e processamento em segundo plano.
- `backend/migrations`: migrações.
- `scripts`: setup, execução e verificações.
- `docs/gitflow.md`: convenções de branches.
- `docs/escopo-atual.md`: ajustes de requisitos aprovados na conversa.
- `docs/plano-desenvolvimento.md`: roteiro por etapas, dependências e critérios de aceite.

Branches `main` e `develop` preparadas; as funcionalidades concluídas estão integradas em `develop`. `main` representa o estado estável já existente. O remoto `origin` está configurado para [Levyhb/rapid-job-search](https://github.com/Levyhb/rapid-job-search), com `main` e `develop` publicadas. Consulte [docs/gitflow.md](docs/gitflow.md) e [docs/publicacao-github.md](docs/publicacao-github.md).

Detalhes dos cargos, regras e comandos manuais: [docs/cargos-e-execucao.md](docs/cargos-e-execucao.md).

Coleta real, fontes suportadas e execução com worker: [docs/coleta-portais.md](docs/coleta-portais.md).

Identificação de plataformas e logs de compatibilidade: [docs/validacao-suporte-portais.md](docs/validacao-suporte-portais.md).
