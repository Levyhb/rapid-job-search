# Gitflow

- main: versões estáveis.
- develop: integração.
- feature/*: sair de develop e retornar para develop.
- release/*: sair de develop; integrar em main e develop; criar tag.
- hotfix/*: sair de main e integrar em main e develop.

Use commits pequenos e descritivos. O remoto GitHub será configurado posteriormente.

## Política de commits — solicitação do usuário em 26/10/2026

Ao terminar de implementar e verificar uma funcionalidade, fazer seu commit imediatamente, sem acumular funcionalidades independentes em um commit geral. Cada commit deve incluir o conjunto coerente de frontend, backend, migrações e documentação daquela entrega.

Exemplos de separação: setup, empresas, cargos, vagas, busca e validação de portais. Mensagens devem descrever o comportamento entregue, usando `feat:`, `fix:`, `chore:` ou `docs:`. Não incluir arquivos temporários, dados locais ou alterações alheias à funcionalidade.

## Entregas já registradas

| Commit | Entrega |
|---|---|
| `9261a0b` | Plano original e Gitflow |
| `2fb0b6b` | Setup de Next.js, FastAPI e serviços locais |
| `30c6f33` | Plano por etapas, identidade e layout base |
| `e7963bb` | Abas de busca e configuração |
| `9a57a70` | Empresas: cadastro no servidor, edição, remoção e JSON |
| `65746c1` | Cargos: cadastro, variações, seleção e prévia |
| `10a51ef` | Regras de cargo e modalidade dos resultados |
| `94d449a` | Coleta dos portais, persistência de vagas, busca em segundo plano e resultados |
| `4fefe13` | Validação automática dos portais e logs estruturados |
| `7ed3a43` | Atalho `py run` para iniciar o backend |

Na entrega `94d449a`, coleta, vagas e busca foram implementadas como um fluxo completo em um único commit. Nas próximas entregas, separar essas frentes em commits próprios quando constituírem funcionalidades independentes. O histórico existente permanece preservado.

## Publicação no GitHub

Configuração do remoto, primeiro envio das branches e proteção por CI: [publicacao-github.md](publicacao-github.md). Funcionalidades concluídas são integradas em `develop`; a publicação inicial não antecipa uma release nem altera o estado estável de `main`.
