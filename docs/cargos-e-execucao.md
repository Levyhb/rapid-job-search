# Cargos e execução local

Implementado em 26/10/2026.

## Cadastro de cargos

Na aba Empresas e cargos, use Adicionar cargo para abrir um formulário vazio. Informe o nome principal, variações aceitas opcionais (uma por linha ou separadas por vírgula) e se o cargo participa das buscas. O menu de três pontos permite editar/remover, com confirmação de remoção e toasts após persistência. A lista tem altura fixa, rolagem própria e filtro por nome ou variação.

Cargos e variações são persistidos no PostgreSQL, tabela `roles`. A migração `20261026_01` cria a tabela. Empresas continuam no JSON do servidor, sem alteração de formato. O resumo da busca conta apenas cargos selecionados; desmarcar não remove o cadastro.

O nome principal é uma alternativa aceita, junto de suas variações. O motor normaliza caixa, acentos, espaços e separadores simples, preservando limites de palavras e frases consecutivas. Não há sinônimos ou traduções ocultas.

- Desenvolvedor inclui Desenvolvedor Backend, Desenvolvedor Java e Analista Desenvolvedor.
- Dev Backend só corresponde quando Dev foi registrado como nome ou variação.
- Dev não corresponde a DevOps; Java não corresponde a JavaScript.
- Full-Stack e Full Stack são equivalentes; Fullstack precisa constar como variação adicional.
- O motor usa apenas o título. A prévia não aceita um campo de descrição para satisfazer a correspondência.
- A modalidade remota é uma regra separada. O helper de modalidade exige evidência estruturada conhecida e exclui presencial, híbrido e desconhecido. Restrições de país serão preservadas pelo coletor futuro, sem inferência automática.

A seção Testar título de vaga chama o backend e informa os cargos selecionados e termos que corresponderam. Ela não consulta portais e não garante modalidade remota; serve para entender a regra.

## Estado do produto

Frontend e backend de empresas e cargos estão integrados. Atualização da etapa de coleta: o backend já libera a busca para as fontes validadas. Empresas, cargos selecionados, Redis e worker ativo são necessários. Veja `docs/coleta-portais.md`.

## Iniciar no Windows

Com Docker Desktop aberto, na raiz do projeto:

```powershell
.\scripts\dev.ps1 infra
```

Depois, em dois terminais separados, ambos na raiz:

```powershell
.\scripts\dev.ps1 frontend
```

```powershell
.\scripts\dev.ps1 api
```

O comando da API aplica migrações antes de iniciar o Uvicorn com reload. Se o banco estiver parado, ele informa que a infraestrutura precisa ser iniciada.

Alternativa manual — terminal do frontend:

```powershell
cd C:\documentos\projetos\busca-vagas\frontend
npm run dev
```

Alternativa manual — terminal do backend:

```powershell
cd C:\documentos\projetos\busca-vagas\backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Não é necessário ativar o venv ao usar seu executável diretamente. Se a política do PowerShell bloquear scripts, use `powershell -ExecutionPolicy Bypass -File scripts/dev.ps1 frontend` ou `api`/`infra`, a partir da raiz.

- Aplicação: http://127.0.0.1:3000
- API/documentação: http://127.0.0.1:8000/docs
- Banco local: PostgreSQL em `127.0.0.1:55432`.
- `Ctrl+C` encerra o serviço no terminal. `docker compose stop` para a infraestrutura preservando os volumes.
- Worker não é necessário para o cadastro; será usado na coleta futura.

## API de cargos

- `GET/POST /api/roles`: lista/cria cargos.
- `PATCH/DELETE /api/roles/{id}`: edita/remove.
- `PATCH /api/roles/{id}/selection`: altera participação na busca.
- `POST /api/roles/preview`: testa `{titulo}` apenas contra cargos selecionados.

Formato de criação/edição: `{nome, variacoes: string[], selecionado: boolean}`. Máximo de 30 variações, com até 120 caracteres cada. Nomes duplicados após normalização retornam conflito. O nome principal não é repetido nas variações; equivalências duplicadas são consolidadas.

## Verificação

- 23 testes do backend passaram, incluindo as verificações anteriores, CRUD/seleção/duplicatas, normalização, frases e limites de palavras, exclusão de descrição e filtro remoto separado.
- Migração aplicada no PostgreSQL real e saúde de PostgreSQL/Redis confirmada.
- Teste de navegador com API/PostgreSQL reais verificou criar, editar, remover, persistência após recarregar, seleção e atualização do contador, filtro, toasts e prévia Dev Backend/DevOps.
- Foco/Escape do modal e viewports 320/390/768 px verificados; dados QA removidos ao terminar.
- Build, ESLint, TypeScript e Ruff verificados.
