# Abas e pesquisa — atualização do layout

## Entregue

- Aba inicial Busca por vagas: resumo de empresas/cargos, botão e seção Vagas encontradas.
- Aba Empresas e cargos: layouts de cadastro, importação/exportação e seleção de cargos.
- Terminologia de produto alterada de palavras-chave para cargos.
- Navegação de abas por clique e teclado (setas, Home e End), com painel ativo identificado para leitores de tela.
- Trocar de aba preserva o acompanhamento de uma execução no frontend.
- Estados de início, busca, contagem recebida da API, conclusão, vazio e resultados paginados preparados para integração real.

## Contrato preparado no frontend

O endpoint de resumo está implementado para empresas desde 25/10/2026, com o total real de cargos selecionados desde 26/10/2026; execução=null e search_available=false enquanto a coleta não existe. Os endpoints de pesquisa abaixo **ainda serão implementados no backend** nas etapas funcionais do roteiro. A entrega atual é a reorganização do frontend. Não há coletor ou busca simulada no produto.

- `GET /api/configuration/summary`: `{company_count, selected_role_count, active_search_id}`. Contagem apenas de cargos selecionados; ID ativo permite retomar acompanhamento após recarregar.
- `POST /api/searches`: retorna HTTP 202 com `{id, status, found_count}`.
- `GET /api/searches/{id}`: mesma estrutura, com status `queued`, `running`, `completed`, `interrupted` ou `cancelled`.
- `GET /api/searches/{id}/jobs?page=1&page_size=20`: `{items: [{id, company, title, url}], total, page, page_size}`.

Requisito confirmado em 26/10/2026 para a implementação desse endpoint: acrescentar a modalidade em cada item (`modality`: `remote`, `hybrid`, `onsite` ou `unknown`) e preservar o rótulo original da fonte no armazenamento. A tabela final terá Nome da empresa | Título da vaga (link) | Remoto/Híbrido. Os tipos/coletores e essa coluna serão implementados na etapa de resultados; o filtro atual continua somente remoto, independentemente da possibilidade de classificar vagas híbridas.

O frontend consulta progresso a cada dois segundos, sem porcentagem inventada; falhas transitórias de acompanhamento são registradas no console e tentadas novamente. Mostra resultados após conclusão, com link HTTP(S) direto e paginação. Não soma falhas na contagem.

Enquanto o resumo real não estiver disponível, os totais exibem “—” e o botão fica desabilitado. Não usar zero para representar dados desconhecidos. O cadastro de empresas já está integrado; o cadastro e os seletores de cargos também estão integrados desde a etapa 4.

## Validação

Verificações realizadas: lint, TypeScript e build; navegação por abas e teclado; estado vazio com a API atual; ausência de overflow em 320, 390 e 768 px. Respostas controladas apenas no teste de navegador validaram resumo 3 empresas/2 cargos, loading, atualização de 7 para 21 vagas, troca de abas durante a execução, conclusão e paginação em duas páginas. Essas respostas não fazem parte do produto nem representam integração real com portais.
