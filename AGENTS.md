# Instruções do projeto RapidJobSearch

## Commits por funcionalidade

- Ao concluir uma funcionalidade nova ou uma correção, executar as verificações adequadas e deixar as alterações sem commit para validação do usuário.
- Nunca executar `git commit` automaticamente. Fazer commit somente após autorização explícita do usuário; informar o resumo das mudanças e das verificações para revisão.
- Separar funcionalidades independentes em commits próprios, por exemplo setup, empresas, cargos, vagas, busca e validação de portais.
- Incluir no commit os arquivos de frontend, backend, migrações e documentação necessários àquela funcionalidade.
- Usar mensagens descritivas em português com prefixo apropriado: `feat:`, `fix:`, `chore:` ou `docs:`.
- Conferir o diff e o status antes de commitar; incluir apenas o trabalho da entrega, preservando alterações alheias.
- Criar e atualizar planos e roteiros somente em `/plans/`, pasta local ignorada pelo Git. O roteiro atual fica em `plans/plano-desenvolvimento.md`.
- Manter em `/docs/` apenas documentação da aplicação, operação e manutenção. Não adicionar planos ao stage nem usar `git add -f` para incluí-los.
- Seguir o Gitflow de `docs/gitflow.md`. Fazer commit local não implica publicar no GitHub ou lançar uma versão.

## Aplicação genérica

- Não adicionar nomes, domínios ou listas de empregadores reais ao código, fixtures ou documentação pública. Usar empresas fictícias e domínios de exemplo nas demonstrações.
- Manter coletores por plataforma e fallback genérico; não criar adaptadores ou regras por empresa.
- Guardar inspeções de empresas e evidências específicas apenas em pastas locais ignoradas pelo Git. Preservar os cadastros reais do usuário.
- Nomes e domínios de plataformas ou serviços técnicos podem aparecer quando necessários à integração; não confundir esses fornecedores com empresas cadastradas para buscar vagas.
