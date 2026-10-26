# Ajustes de escopo — atualizado em 26/10/2026

Os pedidos mais recentes do usuário prevalecem sobre os pontos conflitantes do plano original.

Nome da aplicação: **RapidJobSearch**. Roteiro de implementação atualizado em `docs/plano-desenvolvimento.md`.

- Cadastro de empresas por nome e URL.
- Empresas salvas em arquivo JSON local (caminho configurável), com importação/exportação compartilhável junto do cadastro. PostgreSQL permanece para configurações, execuções e vagas; o catálogo JSON será a fonte do cadastro.
- Cargos como opções alternativas no título da vaga, como fullstack, backend ou frontend.
- Manter as regras aprovadas: ignorar caixa, acentos e separadores simples; respeitar palavras completas (Dev não inclui DevOps); procurar cargos apenas no título; avaliar modalidade separadamente do cargo.
- Somente vagas remotas; a interpretação inicial é exigir confirmação dessa modalidade.
- Resultados futuros: **Nome da empresa | Título da vaga (link) | Remoto/Híbrido**. Armazenar a modalidade informada pela fonte e sua classificação normalizada, sem inferir pela empresa ou pelo cargo. A coluna não habilita vagas híbridas: o filtro atual continua somente remoto.
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

Frontend, backend, infraestrutura e ferramentas estão preparados. O layout base do RapidJobSearch e seu CSS global foram implementados; as funcionalidades de domínio seguem as próximas etapas do roteiro.
