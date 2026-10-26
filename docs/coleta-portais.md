# Coleta de vagas — primeira integração real

Implementada e validada em 26/10/2026.

## Fontes verificadas

| Empresa | Link cadastrado | Leitura utilizada | Anúncios examinados na validação | Indicação de remoto, antes do filtro por cargo |
|---|---|---|---:|---:|
| Alice | https://alice.inhire.app/vagas | Resposta pública InHire `job-posts/public/pages`, tenant alice | 17 | 3 |
| Afya | https://afya.gupy.io/ | `__NEXT_DATA__` público da página, contendo a listagem completa | 146 | 8 |
| Arco | https://www.arcoeducacao.com.br/carreiras#grnhse_app | Identificação do embed Greenhouse e API pública do board `arcoeducacao` | 51 | 11 |

Essas quantidades são uma observação da data da validação e mudam com as publicações. As três empresas foram mescladas no catálogo real, sem remover cadastros existentes. O JSON compartilhável está em `docs/empresas-primeira-coleta.json`.

## O que significa cobrir a paginação

As três interfaces dividem visualmente as vagas, mas disponibilizaram publicamente a coleção completa nos dados usados para montar a tela. O coletor lê essa coleção inteira com HTTPX, processando lotes de dez anúncios e verificando IDs/total. Não limita a consulta à primeira página nem aplica os filtros de texto do portal.

Na Afya, a página inicial entregou 146 registros embora a interface mostrasse dez por página. A inspeção com Playwright abriu a página 15 e confirmou que a última vaga exibida estava na coleção do coletor. Na Alice, a resposta pública continha 17 vagas, incluindo as que não aparecem no primeiro grupo de dez da interface. Na Arco, `meta.total=51` foi comparado com os anúncios recebidos.

Quando o total processado não confere com o informado, a coleta é parcial e o motivo fica no diagnóstico. Se uma fonte futuramente passar a fornecer apenas a primeira página, o adaptador precisará ser revisto; não há um navegador universal que promete navegar qualquer portal.

## Ferramentas e fluxo

1. Next.js envia `POST /api/searches` para o FastAPI.
2. A API salva uma cópia das empresas e dos cargos selecionados no PostgreSQL e envia a tarefa para RQ/Redis. Uma execução ativa por vez evita trabalho conflitante.
3. O worker Linux executa os coletores HTTPX. Playwright é usado para validação real de navegação/links; não é necessário abrir Chromium durante essas três leituras públicas.
4. Cada anúncio é classificado por modalidade, preservando o rótulo e a localidade da fonte. Remoto é aceito; híbrido, presencial e desconhecido ficam fora dos resultados atuais. Uma modalidade contraditória fica desconhecida.
5. O título é comparado com os cargos e variações salvos: palavras/frases completas, caixa/acentos/separadores normalizados, sem sinônimos ocultos e sem usar a descrição para satisfazer cargo.
6. Vagas compatíveis são deduplicadas pela identidade da fonte e persistidas antes de aumentar o contador. Uma vaga que corresponde a vários cargos continua com uma linha.
7. O frontend consulta o progresso a cada dois segundos e apresenta a tabela final paginada: Empresa | Título da vaga (link) | Remoto/Híbrido.
8. Recarregar a aplicação recupera a execução ativa ou a última execução salva. Alterações no cadastro durante uma busca só valem para a próxima.

## Falhas e limites

- Timeout de requisição de 25 segundos, uma repetição em falha de transporte, máximo de 10.000 anúncios e orçamento de 180 segundos de coleta/processamento por fonte.
- HTTP 401/403/429 é registrado como bloqueio; não se tenta contornar proteção ou login.
- Fonte ainda sem adaptador validado é classificada como não suportada.
- Anúncios inválidos não apagam os válidos; geram coleta parcial. IDs repetidos não geram linhas extras.
- Uma fonte que falha não impede as outras. Falhas/parciais ficam nos logs do worker e em `console.log` no navegador, sem mensagem de erro por empresa na interface e sem entrar na quantidade de vagas.
- A execução pode terminar com fontes incompletas: o total final representa o que foi efetivamente encontrado, sem promessa de cobertura completa de todas as fontes.
- Erros de enfileiramento liberam a execução ativa. Falhas do worker são reconciliadas com RQ no acompanhamento; uma falha temporária de Redis sozinha não prova interrupção.
- Não há agendamento, candidatura automática ou cancelamento pela interface nesta entrega.

## Como executar

Com Docker Desktop aberto, na raiz do projeto:

```powershell
.\scripts\dev.ps1 infra
```

Em terminais separados:

```powershell
.\scripts\dev.ps1 api
```

```powershell
.\scripts\dev.ps1 frontend
```

```powershell
.\scripts\dev.ps1 worker
```

O script da API aplica as migrações. O worker precisa estar ativo para a tarefa ser aceita. Para deixá-lo em segundo plano, use `docker compose --profile worker up -d --build worker`. Depois de mudar código de coleta, reinicie o worker com `docker compose restart worker`.

Na aplicação, confira as empresas, cadastre/selecione ao menos um cargo e clique em Buscar vagas. Nenhum cargo foi criado como padrão oculto. A primeira compilação do contêiner pode baixar Chromium e dependências porque o ambiente também mantém Playwright disponível para novas fontes.

## Verificação realizada

- 33 testes do backend: fontes, cobertura além da primeira página, lote incompleto, limites, bloqueios, modalidade, anúncio inválido, snapshot imutável, deduplicação, falha isolada, recuperação e paginação, além dos testes anteriores.
- Consulta real às três fontes: 214 anúncios examinados, 22 com indicação remota antes do filtro de cargos.
- Fila RQ real + worker Linux + PostgreSQL + tela: com cargos de teste explicitamente configurados (Analista, Engineer, Desenvolvedor, Dev), a execução retornou 11 vagas reais compatíveis e remotas, sem falhas de fonte.
- Link direto da Alice e última vaga da página 15 da Afya conferidos em Chromium.
- Resultados, terceira coluna e recuperação após recarregar conferidos; layout móvel mantém rolagem horizontal apenas dentro da tabela.
- Cargo e execução criados exclusivamente para QA foram removidos após a validação. Permanecem as três empresas fornecidas pelo usuário; não foram adicionadas vagas fictícias.

## Referências

- API pública Greenhouse: https://docs.greenhouse.io/job-board.html
- Portais InHire/Alice e Gupy/Afya inspecionados diretamente nos links fornecidos. As estruturas desses dois portais são dependências observadas, não uma promessa de API pública versionada e estável.
