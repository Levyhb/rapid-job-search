# Cadastro de empresas no servidor

Implementado em 25/10/2026.

## Uso

Na aba **Empresas e cargos**, use **Adicionar empresa** para abrir um formulário vazio com nome e link. Cada salvamento adiciona uma empresa. O menu de três pontos permite editar ou remover; a remoção pede confirmação. As três operações exibem toast após a confirmação do servidor.

As linhas têm altura fixa de 62 px, no formato Nome | Link | Ações. A região da lista tem altura de 360 px e rolagem vertical própria. Nomes e URLs longos são truncados visualmente; o valor completo aparece ao passar o mouse. O filtro por nome ignora caixa e acentos e não altera o catálogo salvo.

**Importar JSON** aceita arquivo UTF-8 de até 2 MB ou texto colado. A prévia informa novas empresas, duplicadas e inválidas. A confirmação importa apenas as válidas revisadas; mescla com o catálogo existente sem removê-lo. A API revalida tudo na gravação. Duplicatas são identificadas por nome normalizado + URL conservadoramente normalizada, preservando caminho e parâmetros.

**Exportar JSON** abre um modal com a lista completa do servidor, independentemente do filtro. **Copiar JSON** copia texto indentado com dois espaços. Caso o navegador bloqueie a área de transferência, o texto é selecionado para cópia manual. IDs internos não aparecem na exportação.

Formato compartilhável (a linha abaixo é apenas exemplo, não dado cadastrado):

```json
{
  "versao": 1,
  "empresas": [
    {
      "nome": "Nome da empresa",
      "url": "https://empresa.com/carreiras"
    }
  ]
}
```

O arquivo `docs/empresas-modelo.json` fornece o formato vazio. A lista real do usuário poderá ser formatada posteriormente, quando fornecida.

## Persistência

- Fonte única do cadastro: `backend/data/empresas.json`, no servidor da API.
- Diretório e arquivo de lock ignorados pelo Git; não são enviados ao GitHub.
- `COMPANIES_FILE` permite definir outro caminho absoluto no ambiente do backend.
- Arquivo ausente significa lista vazia. Arquivo inválido gera erro de cadastro e é preservado para recuperação; nunca é substituído por uma lista vazia.
- Escrita em arquivo temporário no mesmo diretório, flush/fsync e substituição atômica. Lock de threads e de arquivo coordena a leitura/modificação/gravação entre processos.
- IDs internos estáveis nas edições; ao importar de outra instalação, novos IDs são gerados.
- Limite de 10.000 empresas por catálogo/importação.
- Não é preciso PostgreSQL ou Redis para o cadastro; continuam previstos para cargos e buscas.
- Se a API for colocada em contêiner no futuro, esse diretório deve ser montado em volume persistente. Hoje a API roda no host e o worker ainda não lê o catálogo.

## API

| Método | Caminho | Comportamento |
|---|---|---|
| GET | `/api/companies` | Lista com ID, nome e URL |
| POST | `/api/companies` | Adiciona `{nome, url}` |
| PATCH | `/api/companies/{id}` | Edita nome/URL mantendo ID |
| DELETE | `/api/companies/{id}` | Remove a empresa |
| GET | `/api/companies/export` | Documento compartilhável completo |
| POST | `/api/companies/import/preview` | Valida e retorna prévia sem gravar |
| POST | `/api/companies/import` | Mescla empresas válidas, ignorando duplicadas |
| GET | `/api/configuration/summary` | Total real de empresas; cargos=0 e execução=null até a implementação dessas funções |

Links aceitos: HTTP/HTTPS sem credenciais. A API não acessa o portal ao cadastrar, portanto salvar não significa que a fonte já foi validada para coleta. Erros de cadastro/importação são exibidos junto à operação; a regra de falhas silenciosas continua aplicável às futuras coletas de portais.

## Validação

- 11 testes do backend: CRUD e persistência, identidade, duplicatas, links inválidos, importação/exportação reversível, importação inválida sem gravação, arquivo corrompido preservado, concorrência entre processos e checks anteriores de saúde/CORS.
- Fluxo no Chromium conectado à API real, com catálogo isolado em `work/`: cadastro vazio, salvar/editar/remover e toasts, filtro com acentos, prévia de importação, duplicatas/linhas inválidas, copiar JSON com indentação, exportar catálogo completo mesmo filtrado, recarregar e atualizar resumo.
- Rolagem e altura fixa verificadas; navegação por teclado, Escape/foco do modal e viewports de 320/390/768 px sem overflow da página.
- Os dados usados na validação são exclusivos do catálogo de teste e não são carregados no cadastro real.

Cadastro de cargos e coleta de vagas continuam nas próximas etapas.
