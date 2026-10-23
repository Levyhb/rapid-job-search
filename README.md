# RapidJobSearch

Painel pessoal para buscar vagas remotas nos portais das empresas cadastradas.

## Estado atual

Ambiente de desenvolvimento e layout base do RapidJobSearch implementados, com CSS global e painel responsivo. O diagnóstico recolhível verifica a conexão real com a API, PostgreSQL e Redis. Cadastro de empresas, importação/exportação JSON, filtros e coleta de vagas serão implementados nas próximas etapas. Os controles pendentes estão desabilitados e a prévia está identificada.

O roteiro de trabalho está em [docs/plano-desenvolvimento.md](docs/plano-desenvolvimento.md). Etapas 0 e 1 concluídas; próxima entrega funcional: cadastro de empresas com persistência JSON.

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

O setup cria os arquivos locais de configuração se não existirem, instala dependências, prepara Chromium, inicia PostgreSQL/Redis e executa migrações. Não é necessário ativar o ambiente virtual. A estrutura Alembic está preparada; ainda não existem tabelas de domínio.

## Executar

Use terminais separados na raiz do projeto:

```powershell
# Terminal 1: API com recarregamento automático
.\scripts\dev.ps1 api

# Terminal 2: frontend com recarregamento automático
.\scripts\dev.ps1 frontend

# Terminal 3, quando necessário: worker Linux
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

O worker é a base de execução; tarefas reais de busca ainda não foram implementadas. Alterações no código montado do worker exigem reiniciá-lo. A execução nativa alternativa `python -m app.workers.main` usa SimpleWorker no Windows, com limitações de isolamento; prefira o contêiner Linux para as coletas.

## Organização e Gitflow

- `frontend/src/app`: interface.
- `backend/app/api`: endpoints.
- `backend/app/core`: configuração e banco.
- `backend/app/collectors`, `filters`, `services`, `workers`: bases para as próximas funcionalidades.
- `backend/migrations`: migrações.
- `scripts`: setup, execução e verificações.
- `docs/gitflow.md`: convenções de branches.
- `docs/escopo-atual.md`: ajustes de requisitos aprovados na conversa.
- `docs/plano-desenvolvimento.md`: roteiro por etapas, dependências e critérios de aceite.

Branches `main` e `develop` preparadas. O setup foi integrado em `develop`; o plano e o layout base estão em `feature/plano-layout`. O remoto GitHub será configurado posteriormente.
