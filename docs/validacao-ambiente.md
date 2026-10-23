# Validação do ambiente

Verificações executadas na entrega inicial:

- Cinco testes da API: saúde, disponibilidade, falha do banco e origens CORS permitida/negada.
- Ruff, ESLint e verificação TypeScript.
- Build de produção do frontend.
- API com PostgreSQL e Redis reais pelo endpoint `/health/ready`.
- Playwright/Chromium no Windows: carregamento da tela, três serviços conectados, atualização pelo botão e viewport móvel sem overflow horizontal.
- Build do contêiner Linux do worker com dependências e Chromium.
- Execução de uma tarefa de verificação na fila RQ e inicialização real do Chromium dentro do contêiner Linux.

O TestClient da versão instalada de Starlette emite um aviso de depreciação do transporte httpx. Os testes passam; a atualização desse transporte pode ser feita com a próxima manutenção das dependências.

Estas verificações validam a infraestrutura. Ainda não existem coletores de portais nem funcionalidades de busca implementadas.
