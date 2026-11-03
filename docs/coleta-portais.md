# Coleta de vagas e integração dos portais

A aplicação consulta os endereços cadastrados pelo usuário. Não há catálogo de
empresas embutido, cadastro automático de fontes nem coletor exclusivo por empresa.

## Estratégias de leitura

| Fonte reconhecida | Leitura |
|---|---|
| InHire | Consulta pública JSON, com o tenant identificado pelo domínio cadastrado |
| Gupy | Dados públicos incorporados no HTML, incluindo `__NEXT_DATA__` quando disponível |
| Greenhouse | API pública do board identificado no domínio ou em um embed inequívoco |
| Outros sites | [Fallback genérico com Playwright](coleta-playwright.md) |

Os adaptadores por plataforma são compartilhados entre seus usuários. Identificar
o domínio não garante que a fonte esteja acessível ou que seu formato permaneça
compatível. Integrações ambíguas, bloqueios e cobertura incompleta produzem
um diagnóstico explícito.

## Fluxo da pesquisa

1. O frontend envia `POST /api/searches` à API FastAPI.
2. A API salva uma cópia das empresas e cargos selecionados e enfileira a tarefa
   no RQ/Redis. Alterações posteriores do cadastro valem para a próxima pesquisa.
3. O worker consulta as fontes por HTTPX e usa o navegador quando o formato exige
   renderização. A coleta simultânea é limitada e a gravação ocorre na thread principal.
4. Cada anúncio conserva empresa, título, URL, localidade e modalidade original.
5. O título é comparado com cargos e variações, normalizando caixa, acentos,
   separadores e flexões previstas. A descrição não satisfaz o filtro de cargo.
6. Apenas vagas remotas confirmadas e compatíveis são persistidas, sem duplicatas.
   Uma vaga que corresponde a vários cargos continua com uma única linha.
7. A interface acompanha a contagem e apresenta resultados paginados e filtros.
   Ao recarregar, recupera a execução ativa ou a última pesquisa salva.

## Cobertura e paginação

Algumas interfaces paginam visualmente, mas disponibilizam a coleção inteira
em seus dados públicos. Nesses casos, o adaptador processa a coleção e compara
IDs únicos e total. Quando a fonte entrega lotes, a coleta deve respeitar sua
paginação e os limites de execução. Não se considera a primeira página como
coleção completa sem evidência.

Quantidade examinada difere de quantidade encontrada: a primeira inclui anúncios
que podem ser presenciais, híbridos ou de outros cargos. O contador de resultados
inclui somente vagas compatíveis salvas.

## Falhas e operação

HTTP 401/403/429, login e desafios de acesso são registrados sem tentativa de
contorno. Uma fonte que falha não impede as demais. Coletas parciais com anúncios
lidos permanecem nos logs como avisos; falhas de consulta entram no modal
**Saber mais**. Veja os [estados e diagnósticos](validacao-suporte-portais.md).

O transporte valida DNS/IP público, TLS, redirecionamentos, tamanho de resposta
e prazo. Os limites e restrições estão em [Segurança](seguranca.md) e
[Coleta com Playwright](coleta-playwright.md).

Para preparar e iniciar infraestrutura, API, frontend e worker, siga o
[README](../README.md#como-rodar-o-projeto). Após alterar o código de coleta,
reinicie o worker quando não houver pesquisa em andamento:

```powershell
docker compose restart worker
```

O [modelo de importação](empresas-modelo.json) contém apenas uma empresa fictícia.
Substitua nome e endereço antes de usá-lo. Os dados cadastrados por cada usuário
ficam separados do código versionado.
