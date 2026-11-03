# RapidJobSearch

## Sobre o projeto

O RapidJobSearch é uma aplicação pessoal para encontrar vagas diretamente nos sites de carreira das empresas, reunindo os resultados em um único painel. Em vez de abrir cada portal manualmente, você cadastra as empresas que deseja acompanhar e os cargos que procura, como Desenvolvedor Backend, Full Stack, Python ou React.

Você não precisa cadastrar cada vaga: **cadastre as empresas e os cargos; a aplicação coleta as vagas**. As empresas podem ser adicionadas individualmente ou importadas de um JSON compartilhável. Os cargos aceitam variações em português e inglês, e você escolhe quais participam da pesquisa.

Ao clicar em **Buscar vagas**, a API cria uma pesquisa e a coloca em uma fila. Um worker Python consulta os portais, compara os títulos com os cargos selecionados, descarta duplicatas e salva as vagas compatíveis. A interface acompanha o progresso e apresenta uma tabela paginada, com empresa, título, modalidade e link para o anúncio. Os filtros avançados permitem refinar os resultados por texto, empresa, cargo e nível. Quando algum site falha, o aviso **Saber mais** mostra os motivos.

A versão atual busca **somente vagas com modalidade remota confirmada** e possui coletores para Gupy, InHire e Greenhouse. A coleta utiliza HTTPX para ler dados públicos JSON ou incorporados no HTML; Playwright/Chromium é usado como fallback para ler páginas renderizadas quando o formato público não é reconhecido. Sites próprios e plataformas diferentes podem precisar de adaptação: cadastrar uma URL não garante que ela seja compatível.

Detalhes da navegação, limites e diagnóstico: [Coleta com Playwright](docs/coleta-playwright.md).

## Como rodar o projeto

As instruções abaixo são para **Windows com PowerShell**. Execute os comandos na ordem indicada. Os caminhos usam a pasta `rapid-job-search`; se seu projeto está em outra pasta, adapte somente os comandos `cd`.

### Tecnologias utilizadas

| Parte | Tecnologias | Para que serve |
|---|---|---|
| Interface | Node.js, Next.js, React, TypeScript e Tailwind CSS | Exibir cadastros, progresso e resultados. |
| API | Python, FastAPI e Uvicorn | Receber requisições e disponibilizar os dados. |
| Banco | PostgreSQL, SQLAlchemy e Alembic | Salvar cargos, pesquisas e vagas; criar/atualizar tabelas. |
| Fila | Redis e RQ | Organizar tarefas de busca em segundo plano. |
| Worker | Processo Python em um contêiner Docker | Executar a coleta dos portais. |
| Coleta e testes | HTTPX e Playwright/Chromium | Consultar fontes públicas e coletar anúncios de páginas renderizadas. |

### 1. Instalar os requisitos

Instale os programas abaixo antes de começar. Depois da instalação, feche e reabra o terminal para atualizar os comandos disponíveis.

| Programa | Versão/configuração esperada |
|---|---|
| Git | Necessário para clonar e atualizar o repositório. |
| Docker Desktop | Com contêineres Linux; conclua a configuração de WSL 2/virtualização caso o instalador solicite. |
| Python | **3.14.10 ou patch posterior da linha 3.14**, com launcher `py`. |
| Node.js | **24.22.1 ou patch posterior da linha 24**, incluindo npm. |

Confira no PowerShell:

```powershell
git --version
docker --version
docker compose version
py -3.14 --version
node --version
npm --version
```

Se algum comando não for reconhecido, confira a instalação e reabra o terminal antes de continuar. Os scripts verificam as versões mínimas de Python e Node; versões de outras linhas não substituem automaticamente as exigidas. As referências estão em `.python-version` e `.node-version`.

**Não é necessário instalar PostgreSQL ou Redis diretamente no Windows**, pois eles serão executados pelo Docker. Também não precisa instalar TypeScript, Next.js ou FastAPI globalmente: o setup instala as dependências do projeto.

### 2. Obter o projeto

Se ainda não tem a pasta do repositório:

```powershell
git clone https://github.com/Levyhb/rapid-job-search.git
cd rapid-job-search
git switch develop
```

Se já clonou, abra o PowerShell na raiz da pasta existente. É a pasta que contém `README.md`, `compose.yaml`, `backend`, `frontend` e `scripts`. **Não execute o setup de dentro de `backend` ou `frontend`.**

### 3. Docker: iniciar banco e Redis

Abra o **Docker Desktop** e aguarde o mecanismo do Docker ficar em execução. Verifique se o terminal consegue se conectar a ele:

```powershell
docker info
```

Na raiz do projeto, execute:

```powershell
docker compose up -d --wait postgres redis
```

Na primeira execução, o Docker baixa as imagens e cria os contêineres e volumes. O `-d` mantém os serviços em segundo plano; `--wait` aguarda a inicialização e os checks de saúde.

```powershell
docker compose ps
```

PostgreSQL e Redis devem aparecer em execução, com estado `healthy`. Se aparecer erro de conexão com o daemon, volte ao Docker Desktop e confira se ele terminou de iniciar.

### 4. Preparar o ambiente pela primeira vez

Com os requisitos instalados e o Docker aberto, execute **na raiz do projeto**:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
```

O script prepara **backend e frontend**:

1. Cria `backend/.env` e `frontend/.env.local` a partir dos exemplos, caso ainda não existam.
2. Cria o ambiente virtual Python em `backend/.venv`, caso esteja ausente, e confere sua versão.
3. Instala as bibliotecas Python de `backend/requirements.txt` e o pacote local do backend.
4. Instala o Chromium do Playwright para coleta e testes de navegação.
5. Instala os pacotes do frontend com `npm ci`.
6. Garante PostgreSQL e Redis ativos e aplica as migrações, que criam/atualizam as tabelas do banco.

**Não precisa criar o venv, ativá-lo ou instalar cada biblioteca manualmente.** O setup já faz a preparação. Ele não inicia a API, o frontend nem o worker. Aguarde a mensagem **Ambiente preparado**; se houver erro, corrija o passo indicado antes de continuar.

O setup pode ser executado novamente para reinstalar as dependências após mudanças nos arquivos de versões. Ele preserva os arquivos `.env` existentes. Se encontrar um ambiente virtual de outra versão do Python, será necessário ajustá-lo antes de prosseguir; o script não o recria automaticamente.

### 5. Docker: construir e iniciar o worker

Ainda na raiz, execute:

```powershell
docker compose --profile worker up -d --build worker
```

Esse comando constrói a imagem Python do worker e o inicia em segundo plano. A primeira construção pode demorar porque baixa dependências e Chromium. O `--profile worker` habilita esse serviço opcional do Compose.

Confira novamente:

```powershell
docker compose ps
```

Agora devem existir **três serviços em execução: `postgres`, `redis` e `worker`**. O worker não possui porta web: ele escuta a fila do Redis e executa as buscas. Banco e Redis ativos sem o worker não são suficientes para pesquisar vagas.

### 6. Backend: iniciar a API

Abra um terminal para a API. Partindo da raiz do projeto:

```powershell
py -3.14 --version
cd backend
py run
```

O atalho `py run` usa o Python de `backend/.venv`, confere sua versão, aplica as migrações e inicia o Uvicorn na porta 8000. Também pode ser executado como `py run.py`.

**`py run` inicia a API; não substitui o setup nem inicia os contêineres.** Deixe esse terminal aberto. A mensagem esperada é semelhante a `Uvicorn running on http://127.0.0.1:8000`.

Abra a [documentação interativa da API](http://127.0.0.1:8000/docs) para conferir se ela respondeu. O endpoint [de disponibilidade](http://127.0.0.1:8000/health/ready) deve indicar PostgreSQL e Redis como `ok`; ele não verifica a presença do worker.

### 7. Frontend: iniciar a interface

Abra **outro terminal**, na raiz do projeto:

```powershell
node --version
npm --version
cd frontend
npm run dev -- --hostname 127.0.0.1
```

As dependências já foram instaladas pelo setup. Deixe esse terminal aberto e acesse [http://127.0.0.1:3000](http://127.0.0.1:3000).

Ao final, você terá dois terminais abertos (API e frontend), além dos três contêineres em segundo plano no Docker.

### Nas próximas execuções

Se o setup já terminou com sucesso e as dependências não mudaram, não precisa repetir toda a instalação. Abra o Docker Desktop e, na raiz, execute:

```powershell
docker compose --profile worker up -d postgres redis worker
```

Depois, repita os passos **6 (backend)** e **7 (frontend)** em terminais separados. Se o worker ainda não tiver imagem, ou seu Dockerfile/dependências tiverem mudado, use novamente o comando com `--build` do passo 5. Após alterar o código Python montado no worker, reinicie-o com `docker compose restart worker`.

### Problemas comuns

| Sintoma | O que conferir |
|---|---|
| `503: Inicie o worker de pesquisa antes de buscar` | Execute o passo 5 e confira `docker compose ps`. Veja os logs com `docker compose logs --tail 50 worker`. |
| `Não foi possível preparar o banco` ou timeout na porta 55432 | Confirme que o Docker Desktop e o serviço `postgres` estão ativos. Confira `DATABASE_URL` em `backend/.env`. |
| `Ambiente virtual não encontrado` ou módulo Python ausente | Execute o setup na raiz antes de usar `py run`. |
| `py`, `node`, `npm` ou `docker` não reconhecido | Instale o programa correspondente e reabra o terminal. |
| Versão de Python ou Node rejeitada | Confira as linhas e patches mínimos do passo 1. |
| Frontend sem conexão com a API | Confirme a API na porta 8000 e `NEXT_PUBLIC_API_URL` em `frontend/.env.local`. |

Configurações locais: `backend/.env` contém conexões com PostgreSQL/Redis e origens CORS; `frontend/.env.local` contém o endereço da API. Os arquivos reais não são versionados. Reinicie os processos após alterar configurações. As credenciais de exemplo do Compose servem somente ao ambiente local. O PostgreSQL usa a porta local **55432** e o Redis usa **6379**.

Para consultar o estado e os logs:

```powershell
docker compose ps
docker compose logs --tail 50 worker
```

### Encerrar o ambiente

Use `Ctrl+C` nos terminais da API e do frontend. Na raiz, pare os contêineres preservando os dados:

```powershell
docker compose --profile worker stop
```

As empresas ficam no JSON local `backend/data/empresas.json`; cargos, pesquisas e vagas ficam no volume PostgreSQL. Uma instalação em outra máquina começa vazia. Clonar o repositório não restaura esses dados: exporte as empresas e mantenha backup do banco se quiser preservá-los.

### Verificações de desenvolvimento

Depois de alterar o código, execute na raiz:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check.ps1
```

O script executa a política estática de segurança, Ruff, testes Python, ESLint, geração de tipos, TypeScript, build do frontend e validação do Compose. A CI do GitHub também executa verificações. Veja os detalhes de runtime e manutenção em [Segurança do ambiente](docs/seguranca.md).

## Como realizar a primeira busca

1. Com todos os serviços ativos, abra [a interface](http://127.0.0.1:3000) e entre na aba **Empresas e cargos**.
2. Em **Adicionar empresa**, informe nome e URL do portal de carreiras. Clique em **Adicionar** para montar a lista e depois em **Salvar** para persistir as empresas. Você também pode usar **Importar JSON** com o [modelo JSON](docs/empresas-modelo.json), substituindo o nome e a URL fictícios pelos dados que deseja cadastrar.
3. Cadastre os **cargos** desejados. Por exemplo, nome `Desenvolvedor Backend` com variações `Backend`, `Back-end Developer` e `Backend Engineer`. Deixe selecionados os cargos que devem participar da busca. Os termos são alternativas: basta um deles corresponder ao título.
4. Volte à aba **Busca por vagas**. Confira as quantidades de empresas cadastradas e cargos selecionados e clique em **Buscar vagas**.
5. Acompanhe o loading e a contagem de vagas encontradas. Depois da conclusão, consulte a tabela, use os filtros avançados e abra o título para acessar o anúncio original.
6. Se aparecer o aviso de sites com falha, clique em **Saber mais** para ver empresas, URLs e motivos. Uma fonte pode precisar de adaptação ou estar bloqueada; as vagas obtidas nas outras fontes continuam disponíveis. Uma coleta bem-sucedida com zero vagas não conta como erro.

As regras consideram acentos, maiúsculas/minúsculas, separadores e flexões como Desenvolvedor/Desenvolvedora, respeitando palavras completas: `Dev` não inclui `DevOps`. A modalidade remota é verificada separadamente. Os filtros de resultados não iniciam uma nova consulta aos sites.

## Organização e Gitflow

| Pasta | Conteúdo |
|---|---|
| `frontend/src/app` e `frontend/src/components` | Telas, componentes e CSS global. |
| `backend/app/api` | Rotas da API FastAPI. |
| `backend/app/core` e `backend/app/models` | Configuração, conexão e modelos de banco. |
| `backend/app/collectors` e `backend/app/filters` | Coleta, normalização e regras de correspondência. |
| `backend/app/services` e `backend/app/workers` | Serviços e tarefas em segundo plano. |
| `backend/migrations` | Migrações Alembic. |
| `scripts` | Preparação, execução e verificações. |
| `docs` | Documentação da aplicação, operação e manutenção. |
| `plans` | Planos e roteiros locais; não devem ser versionados. |

`main` recebe as versões estáveis; `develop` integra as próximas implementações. Crie branches `feature/nome` a partir de `develop` atualizada e abra um PR de volta para ela. Releases usam `release/*`; correções urgentes de versões publicadas usam `hotfix/*`.

Consulte o [Gitflow completo](docs/gitflow.md), o [histórico de alterações](CHANGELOG.md), os guias de [empresas](docs/cadastro-empresas.md), [cargos](docs/cargos-e-execucao.md), [coleta](docs/coleta-portais.md), [filtros](docs/filtros-avancados.md) e [diagnósticos dos portais](docs/validacao-suporte-portais.md). Para configurar outro remoto, veja [Publicação no GitHub](docs/publicacao-github.md).
