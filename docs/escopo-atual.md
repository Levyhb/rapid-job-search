# Ajustes de escopo — 23/10/2026

Os pedidos mais recentes do usuário prevalecem sobre os pontos conflitantes do plano original.

- Cadastro de empresas por nome e URL.
- Empresas salvas em formato JSON, com importação/exportação compartilhável junto do cadastro; definir a persistência física ao implementar o cadastro, preservando esse contrato.
- Palavras-chave alternativas no título da vaga, como fullstack, backend ou frontend.
- Somente vagas remotas; a interpretação inicial é exigir confirmação dessa modalidade.
- Percorrer páginas/lotes dos portais e apresentar resultados paginados na aplicação.
- Botão de pesquisa com loading, contagem progressiva de vagas compatíveis únicas e lista final com links.
- Falhas de coleta por empresa somente nos logs do backend e no console do navegador, sem erro na tela ou alteração artificial na contagem; continuar nas demais empresas.
- Histórico, favoritos e perfis avançados do plano original ficam fora desta implementação de ambiente.

Formato de intercâmbio proposto:

```json
{
  "versao": 1,
  "empresas": [
    { "nome": "Empresa A", "url": "https://empresa-a.com/carreiras" }
  ]
}
```

Esta entrega prepara frontend, backend, infraestrutura e ferramentas. As funcionalidades de domínio serão implementadas posteriormente.
