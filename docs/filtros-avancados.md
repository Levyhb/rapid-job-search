# Filtros avançados de resultados

Na seção **Vagas encontradas**, abra **Filtros avançados**. A busca por nome considera título e empresa, ignorando caixa e acentos. Empresa e cargo são seleções únicas com busca interna; as opções vêm dos cadastros atuais por GET, com loading independente por campo e nova tentativa em caso de falha.

Os filtros são combinados e aplicados às vagas da execução concluída, antes da paginação. Ao alterar qualquer filtro, a página volta para 1. A contagem junto da tabela corresponde ao resultado filtrado; a contagem da pesquisa finalizada permanece como total coletado. Fechar a seção preserva a seleção. **Limpar filtros** restaura os resultados completos. Filtrar não inicia uma nova coleta.

## Níveis iniciais

Conforme combinado, são um catálogo inicial fixo, sem tela de cadastro nesta entrega:

| Nível | Termos reconhecidos no título |
|---|---|
| Júnior | Júnior, Junior, JR |
| Pleno | Pleno, PL |
| Sênior | Sênior, Senior, SR |
| Especialista | Especialista, Specialist |

Cargo usa o nome e as variações do cadastro atual, incluindo cargos desmarcados para novas coletas. Cargo e nível usam palavras completas, ignorando acentos, caixa e separadores simples. Não há inferência de senioridade pela descrição; títulos sem indicação de nível permanecem visíveis com **Todos os níveis**. Sênior e Especialista são separados.

## API e implementação

- `GET /api/companies` e `GET /api/roles`: opções dos selects.
- `GET /api/searches/levels`: níveis e variações iniciais definidos em `backend/app/filters/levels.py`.
- `GET /api/searches/{id}/jobs`: novos parâmetros opcionais `q`, `company_id`, `role_id`, `level_id`, combinados com `page` e `page_size`. IDs inválidos retornam 422. Sem filtros mantém a paginação anterior.
- Empresa restringe pelo nome registrado nas vagas da coleta. Renomear uma empresa não reescreve resultados históricos; uma nova coleta usa o cadastro atualizado.
- Texto/cargo/nível são comparados no backend antes do recorte de página, usando a normalização dos cargos. A digitação no campo de nome aguarda 300 ms antes de consultar; mudanças abortam requisições anteriores para evitar respostas antigas substituindo resultados recentes.

## Validação

46 testes do backend aprovados, incluindo combinação dos filtros, contagem e paginação entre páginas, acentos, abreviações, limites de palavras, IDs inválidos e preservação do total da coleta. Lint, TypeScript e build do frontend aprovados.

No Chromium, com respostas de pesquisa controladas e sem alterar os dados reais: loading independente, catálogo completo de empresas, busca nos selects, navegação por teclado/Escape, seleção única, combinação, retorno à primeira página, estado vazio, limpar/reabrir, falha de opções e nova tentativa, viewports de 320/390 px sem overflow horizontal.
