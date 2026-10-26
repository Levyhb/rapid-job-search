# Inspeção dos portais que falharam — 26/10/2026

Inspeção das 18 fontes não concluídas na execução `5ae37636-2962-4c8e-82ef-a9e91424ca50`, usando as URLs atuais do cadastro. A Meta foi atualizada pelo usuário para `https://insi.jobs.recrut.ai/vagas`; o site se apresenta como Insi. O nome no cadastro foi preservado.

Foram usados Chromium/Playwright para observar DOM, redirecionamentos e respostas de rede, e HTTPX para testar leitura direta e paginação. Apenas páginas, scripts e endpoints públicos de consulta foram acessados; nenhum formulário de candidatura foi enviado. As quantidades abaixo são observações da inspeção, não vagas compatíveis com o perfil nem garantias de estabilidade da fonte.

## Resultado por empresa

| Empresa | Evidência confirmada | Caminho para adaptação |
|---|---|---|
| Meta / Insi | Recrut.AI: página e consulta de vagas retornaram HTTP 200. Resposta JSON com fragmento HTML, links individuais e modalidade por linha. Mais de 100 anúncios observados. | HTTPX + parser do fragmento HTML. Substitui a investigação do antigo HTTP 429 pela implementação de um adaptador Recrut.AI. |
| DBC | API pública retornou 48 registros, embora a tela mostre 15 por página. `id`, `name`, descrições e `workType.description` estão estruturados. | HTTPX; converter a lista completa, respeitar modalidade e descobrir os links de detalhe usados pelo portal. |
| Avanade | A interface consultou Coveo por POST, com 12 resultados por resposta. A resposta filtrada por Brazil informou 50; uma requisição inicial global informou 693. Consulta HTTP sem inicialização do portal retornou 401. | Adaptador Coveo com inicialização do mecanismo público de busca. Validar obtenção/renovação do token do frontend; Playwright é candidato ao bootstrap/fallback. Não tratar a primeira página como coleção completa. |
| CI&T | HTML inicial contém 200 URLs distintas de candidatura com `opportunity=<UUID>` e rótulos de modalidade, incluindo `Workplace_type_Remote`. | HTTPX + parser dos cards. Validar a cobertura total e o vínculo entre título, modalidade e URL antes de liberar o adaptador. |
| Cloudwalk | HTML inicial contém 22 links de anúncios e dados serializados do Next.js com `jobs`, `id`, `title`, `location_type` e localidade. Foram observados 18 registros com `location_type=remote` nesse payload. | HTTPX; extrair os dados serializados com parser apropriado e preservar os links do site. Não precisa navegar card por card para obter a listagem observada. |
| Escavador | HTML e scripts públicos identificaram `/api/vagas?page=N`; o código percorre `data` e `last_page`. A rota de vagas retornou HTTP 403 e o Chromium recebeu tela Cloudflare nesta tentativa. O HTML inicial também chegou a responder 200, sem vagas carregadas. | Rota identificada, acesso inconclusivo/bloqueado. Manter diagnóstico de bloqueio; Playwright também encontrou o desafio. Não há validação de leitura completa dessa API. |
| GFT | SAP SuccessFactors: vagas já no HTML, títulos em `jobTitle-link`, modalidade em `jobShifttype`. Página 1: 1–25 de 55; página seguinte confirmada: 26–50. | HTTPX + parser HTML; seguir os links de paginação, inclusive a última página. Preservar rótulos mistos como Remote / Hybrid, sem assumir remoto exclusivo. |
| Ifood | `__NEXT_DATA__` contém `pageProps.jobs`, apontando para o board Greenhouse `ifoodcarreiras`. API Greenhouse retornou 55 vagas e `meta.total=55`. | Descobrir automaticamente o board pelo site institucional e reutilizar o coletor Greenhouse. O coletor existente, chamado diretamente com esse board para inspeção, concluiu 55/55 e reconheceu 7 remotas. |
| Linx | HTML contém a vaga, código, título, localidade e URL individual no domínio TOTVS. Um link distinto de anúncio observado. | Parser HTML compartilhado com TOTVS. Confirmar modalidade no anúncio; `data-remote-string="Remoto"` é um rótulo de apresentação, não prova de que toda vaga seja remota. |
| Picpay | Oracle Candidate Experience. Requisição pública de listagem retornou dados estruturados, incluindo `TotalJobsCount`, `requisitionList`, `WorkplaceType` e `WorkplaceTypeCode`. Um anúncio retornado nesta inspeção. | HTTPX + adaptador Oracle, com parâmetros do site `CX_3001`, paginação e detalhes. O link cadastrado contém filtro de publicação de 30 dias; uma consulta de inspeção sem esse filtro também retornou um anúncio. |
| Skeelo | HTML inicial contém 12 links de vagas Rippling e payload serializado com departamento, localidade e `workplaceType`. Foram observadas 11 indicações `REMOTE` no payload. | HTTPX; parser da lista incorporada, preservando links Rippling e modalidade por anúncio. Validar a totalidade e detalhes antes de concluir suporte. |
| Stone | A URL antiga abre a página `/vagas-abertas?times=Tecnologia`. A interface mostra 15 resultados em 3 páginas. Resposta da aplicação expõe 7 boards Greenhouse de tecnologia. Os 7 feeds públicos foram consultados: 15 anúncios no conjunto; classificador atual reconheceu 12 remotos, concordando com o filtro da interface. | Reutilizar Greenhouse com múltiplos boards e deduplicação. A identificação atual aceita um único board, por isso não reconheceu esse portal. A inspeção não demonstrou necessidade de Playwright para a leitura das vagas após descobrir os boards. |
| Thomson Reuters | Redireciona para Workday. POST público retornou total 486 na primeira página; duas páginas de 20 trouxeram 40 links distintos. `remoteType` aparece na listagem. | HTTPX + adaptador Workday com `limit`/`offset`. A segunda resposta informou `total=0` mesmo trazendo 20 itens; preservar o total inicial e validar término por conteúdo, sem encerrar prematuramente. |
| TOTVS | HTML inicial contém 301 URLs distintas de anúncios com título/código/localidade. A estrutura é a mesma da Linx e inclui bancos de talentos. | Parser compartilhado com Linx; validar situação dos anúncios, modalidade e cobertura. Não usar um rótulo genérico de remoto como evidência para todos. |
| Valtech | O HTML aponta para endpoint JSON de vagas. Total 156; primeira resposta com 100, segunda com 56; 156 IDs distintos confirmados. Campos incluem título, URL, escritórios e tags. | HTTPX + paginação por offset. Localidades como Brazil - Remote permitem classificação, preservando restrições geográficas. |
| Zenvia | Site institucional chama proxy WordPress/Gupy e links levam a `zenvia.gupy.io`. O proxy retornou 10 registros, mas o próprio JS filtra status/publicação/prazo. O coletor existente validou o portal Gupy direto com 5 anúncios, dos quais 4 remotos. | Descobrir o link do Gupy e reutilizar o coletor existente. Não considerar todos os registros do proxy como vagas abertas. |
| Trevora | HTML inicial contém 3 cards, com título, modalidade Remoto e links individuais `/trabalhe-conosco/...`, incluindo banco de talentos. | HTTPX + parser dos cards e detalhes; preservar o link da vaga e diferenciar banco de talentos de anúncio de cargo. |
| South System | Página institucional aponta para Jobii. A interface chamou API pública paginada: 45 registros em 3 páginas de 15. Todas as páginas foram consultadas: 45 IDs distintos; 39 com `workFormat=Remoto`. | HTTPX + adaptador Jobii, seguindo o vínculo publicado pela South System. Preservar a origem desse vínculo para não atribuir automaticamente qualquer portal Jobii à empresa errada. |

## Endpoints e estruturas observados

Estes caminhos foram observados nas páginas ou na rede e testados como consultas públicas quando indicado acima. Não são contratos oficiais de estabilidade.

- DBC: `GET https://ecos.dbccompany.com.br/api/external-recruitments/vacancies/public`.
- Recrut.AI / Insi: `GET https://insi.jobs.recrut.ai/company/public-jobs/vagas/*/*/*/?search=`; JSON contém `html`.
- Escavador: `GET https://vagas.escavador.com/api/vagas?page=1`, bloqueado nesta inspeção. Nenhuma rota administrativa foi consultada.
- iFood: `GET https://boards-api.greenhouse.io/v1/boards/ifoodcarreiras/jobs?content=true`.
- Valtech: `GET https://www.valtech.com/joblist/getjsonresult?id=1571&language=pt-BR&limit=100&offset=0`, seguido de offset 100.
- Workday: `POST https://thomsonreuters.wd5.myworkdayjobs.com/wday/cxs/thomsonreuters/External_Career_Site/jobs`, corpo de consulta com `appliedFacets`, `limit`, `offset`, `searchText`.
- PicPay: `GET /hcmRestApi/resources/latest/recruitingCEJobRequisitions` no domínio Oracle cadastrado, com `finder=findReqs;siteNumber=CX_3001,...`, limite e offset internos do finder. Não confundir a paginação externa da resposta REST com `requisitionList`.
- Zenvia: `GET https://zenvia.com/wp-json/gupy/v2/jobs`; leitura via portal Gupy direto validada separadamente.
- Jobii: `GET https://services.jobii.com.br/portal/jobs?page=0&size=15&`, depois páginas 1 e 2. Usa `content`, `totalElements`, `totalPages` e `last`.
- Coveo / Avanade: POST no host `avanadesc9productionlk3bs0x7.org.coveo.com/rest/search/v2`. A execução no navegador usa filtros, total e lotes de resultados; bootstrap público ainda exige validação própria.

Boards Stone de tecnologia observados e testados:

| Board | Anúncios | Remotos reconhecidos pelo classificador atual |
|---|---:|---:|
| `jornadatecnologiaengenharia` | 11 | 9 |
| `jornadatecnologiadados` | 2 | 1 |
| `jornadatecnologiadesign` | 0 | 0 |
| `jornadatecnologiaoutrasvagas` | 0 | 0 |
| `jornadatecnologiaproduto` | 2 | 2 |
| `jornadatecnologiasegeinfra` | 0 | 0 |
| `jornadatecnologiapcd` | 0 | 0 |

## Sequência sugerida para implementar

1. Descoberta de plataformas já suportadas: iFood/Greenhouse, Zenvia/Gupy e Stone/Greenhouse com múltiplos boards.
2. Adaptadores públicos com dados claros: DBC, Recrut.AI (Meta/Insi), Jobii (South System) e Valtech.
3. Parsers de HTML e payloads do site: GFT, CI&T, Cloudwalk, Skeelo, Trevora e um único parser para Linx/TOTVS. Trevora tem 3 cards com links `/trabalhe-conosco/...` e modalidade Remoto por card no HTML inicial; não requer navegador para essa listagem observada.
4. Oracle/PicPay e Workday/Thomson Reuters: paginação, geografia e modalidade cuidadosamente validadas.
5. Avanade/Coveo: inicialização e paginação, usando Playwright se necessário ao bootstrap.
6. Escavador: revalidar acesso permitido à rota pública; registrar bloqueios sem tentar resolver desafios automaticamente.

## Limites desta entrega

A inspeção identificou caminhos de adaptação para 17 fontes e uma fonte com rota identificada mas acesso bloqueado (Escavador). Não equivale à liberação dos 17 adaptadores em produção. A modalidade precisa ser avaliada por vaga; menções institucionais a trabalho remoto não bastam. Os resultados brutos podem incluir outros países, cargos, bancos de talentos e vagas híbridas/presenciais.

Evidências completas, HTML, respostas JSON e capturas locais estão em `work/inspecao-portais/`, ignorado pelo Git. Nenhum cookie, token ou header de sessão foi incorporado a esta documentação. Cadastros e resultados do usuário não foram modificados por esta inspeção.
