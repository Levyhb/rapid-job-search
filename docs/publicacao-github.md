# Preparar e publicar no GitHub

O projeto tem Git local e branches `main` e `develop`. A preparação inclui CI, documentação e exclusão dos dados locais. Remoto `origin` configurado para [Levyhb/rapid-job-search](https://github.com/Levyhb/rapid-job-search). As branches `main` e `develop` foram publicadas em 27/10/2026, preservando o histórico local.

## O que será compartilhado

Código, migrações, testes, locks de dependências, scripts, arquivos `.env.example` e documentação. Os JSONs em `docs/` são exemplos compartilháveis. O catálogo real em `backend/data/`, bancos, logs, ambiente virtual, dependências e arquivos `.env` ficam fora do Git.

O GitHub recebe também o histórico dos commits publicados. Ignorar um arquivo não remove uma cópia que já tenha sido commitada. Antes de publicar, revise o histórico e os arquivos preparados com:

```powershell
git status --short
git ls-files
git log --oneline --all
git remote -v
```

As credenciais `busca_vagas` / `local_dev` são exemplos de desenvolvimento local presentes no Compose e nas configurações de exemplo. Não use esses valores em produção. A aplicação atual é pessoal e não possui autenticação; publicar o código não configura hospedagem nem torna a aplicação adequada para exposição pública.

## Criar o repositório

1. No GitHub, crie um repositório chamado `RapidJobSearch` (ou outro nome de sua preferência).
2. Escolha a visibilidade desejada.
3. Crie o repositório vazio, sem gerar README, `.gitignore` ou licença, pois o projeto já tem histórico local.
4. Copie a URL HTTPS ou SSH fornecida pelo GitHub.

Não foi atribuída uma licença de distribuição nesta preparação. Se quiser permitir reutilização como software livre, escolha uma licença antes da publicação e adicione seu arquivo `LICENSE`.

## Primeiro envio

Execute na raiz, substituindo `SEU_USUARIO` e o nome do repositório pela URL real:

```powershell
git remote add origin https://github.com/SEU_USUARIO/RapidJobSearch.git
git remote -v
git push -u origin main
git push -u origin develop
```

Se `origin` já existir, confira sua URL antes de alterá-la. Autentique-se pelo gerenciador de credenciais do Git ou pela chave SSH; não coloque tokens na URL nem em arquivos versionados.

A branch `main` mantém o estado estável já existente. `develop` contém as funcionalidades atuais e esta preparação. O primeiro envio não cria uma release nem integra automaticamente `develop` em `main`.

## Configuração após o envio

- Acompanhe os jobs Backend, Frontend e Configuração Docker Compose na aba Actions. A primeira execução no GitHub ainda precisa confirmar o resultado no runner Linux.
- Use `develop` como base dos PRs de funcionalidades, conforme [Gitflow](gitflow.md).
- Configure regras de proteção para `main` e `develop`, exigindo PR e os checks acima. Os nomes ficam disponíveis após a primeira execução do workflow.
- Habilite alertas de dependências e detecção de segredos quando disponíveis para o repositório.
- Evite anexar exportações pessoais, dumps, logs ou capturas com credenciais em issues e PRs.

## Próximas contribuições

```powershell
git switch develop
git pull --ff-only origin develop
git switch -c feature/nome-da-funcionalidade
# Implementar e executar scripts/check.ps1
git add caminho/dos/arquivos
git commit -m "feat: descreve a funcionalidade"
git push -u origin feature/nome-da-funcionalidade
```

Abra um PR para `develop`. A primeira release segue a etapa 9 do [roteiro](plano-desenvolvimento.md), após a validação integrada; a preparação para o GitHub não conclui essa etapa.
