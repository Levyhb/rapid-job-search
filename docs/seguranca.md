# Segurança do ambiente local

## Manutenção e revisão

Dependabot está configurado para npm, pip, Dockerfile, Compose e Actions.
As versões Python fixadas foram preservadas no novo nome `backend/requirements.txt`,
reconhecido pelo ecossistema pip. Não houve atualização geral de bibliotecas.
Next/React têm grupos coerentes somente para patch/minor; mudanças maiores
ficam separadas. Rotina semanal abre PRs em develop; correções de segurança
npm/pip usam a branch padrão e devem seguir o fluxo de hotfix, sincronizando
main/develop após revisão. Nenhum merge automático foi configurado.

Os SHAs de checkout/setup-python/setup-node foram consultados nos repositórios
oficiais actions em 30/10/2026 e fixados no CI. O workflow existente também
roda semanalmente. Isso prepara enforcement, mas não demonstra execução
no GitHub: o bot depende da configuração integrada na branch padrão e dos
alertas/security updates habilitados no serviço. Não mudamos configurações
remotas nem proteções de branch nesta entrega.

Triar alertas relevantes prontamente; exigir testes e revisão antes de merge.
Uma falha de ferramenta ou base de advisories nunca deve ser considerada scan
limpo. Atualizações de Docker não atualizam o runtime local automaticamente;
conferir `.python-version`, Dockerfile, `.node-version` e engines no mesmo PR.
Não rebaixar versões nem desativar checks para aceitar um update. Exceções
precisam de responsável, motivo, escopo e prazo. Rollback por commit/release,
sem reexpor segredo revogado. Backups e restauração continuam exigindo
procedimento operacional próprio; volume persistente não prova restore.

Não foi instalado scanner ou enviado código/locks a scanner externo. O
cruzamento exaustivo de advisories, histórico de segredos e configuração
implantada permanece trabalho de verificação, não problema automaticamente
resolvido pela configuração do bot.

`scripts/security_checks.py` usa apenas a biblioteca padrão e Git: bloqueia
patch antigo/desalinhado, actions sem SHA completo, pins Python inválidos e
quatro padrões de segredos, imprimindo somente caminho/linha/regra. Falha de
leitura/formato/Git encerra com código diferente de zero. Roda no check local
e em job próprio no CI; não é hook opcional nem scanner de CVEs. Não cobre
histórico, binários, arquivos ignorados ou todos os formatos de credencial.

Verificação local: configuração válida passou; em cópia temporária, patch
antigo, action por tag, token fictício e JSON inválido causaram falha como
esperado, sem imprimir o token. YAML foi lido com parser e as 45 versões
Python foram comparadas com o arquivo anterior, sem mudanças de versão.

## Node.js

A versão mínima de segurança da linha 24 é 24.22.1; `.node-version` fixa a
versão usada no CI. `engines` e `.npmrc` impedem instalar o frontend com um
runtime anterior. Os scripts setup/check/dev preferem o Node portátil em
`work/security-runtimes/node-v24.22.1-win-x64` quando presente e verificam o
patch antes de usar npm. O diretório work é ignorado pelo Git.

Nesta máquina foi extraída a distribuição oficial Windows x64, com SHA256
conferido contra SHASUMS256.txt da mesma versão em nodejs.org. Node global
e PATH persistente não foram alterados. Em outras máquinas, instale um patch
suportado da linha 24 ou prepare a distribuição portátil oficial verificada.
Não basta editar o arquivo de versão: processos antigos devem ser reiniciados.

Node 24.22.1 validado com lint, tipos de rotas, TypeScript e build de produção
do frontend em cópia temporária sem `.env`. O build Turbopack exigiu dependências
copiadas dentro da raiz isolada; uma tentativa anterior com junction externo
foi recusada pelo resolvedor do bundler e não foi tratada como sucesso.

O RapidJobSearch é um painel pessoal, sem contas ou isolamento entre usuários.
Mantenha API, frontend e bancos em loopback. Publicar o código não autoriza
hospedar a aplicação abertamente: autenticação, autorização e revisão de
origens/Host/CSRF são requisitos para uma futura hospedagem.

## Python

O runtime Python de referência é 3.14.10, fixado em `.python-version`, no CI
e na imagem Docker. Os scripts e o atalho `py run` conferem o interpretador
efetivo do venv antes de executar migrações ou iniciar a API.

Nesta máquina o Python Install Manager extraiu o runtime oficial com índice
assinado para `work/security-runtimes/python-3.14.10` usando `--target`, sem
substituir a instalação global. O venv foi atualizado com `venv --upgrade
--without-pip`, preservando pacotes; backup dos scripts e pyvenv.cfg está em
work/security-runtimes. Não remova o runtime portátil enquanto o venv o usa.

Para atualizar outra máquina Windows com o gerenciador oficial:

```powershell
py install --target .\work\security-runtimes\python-3.14.10 3.14.10
.\work\security-runtimes\python-3.14.10\python.exe -I -m venv --upgrade --without-pip backend/.venv
```

Atualizar arquivos não muda processos já iniciados: reinicie API e worker
quando for aplicar o código. A imagem fixada precisa de rebuild; a auditoria
não demonstrou a versão de um contêiner já em execução.

Os 88 testes do backend e Ruff passaram novamente com Python 3.14.10.
O daemon Docker estava indisponível nesta máquina: a imagem não foi
reconstruída e a eficácia em contêiner permanece pendente de verificação.

## Saída HTTP do coletor

Coleta e validação de portais usam a mesma política: somente HTTP(S), portas
80/443, sem credenciais na URL. Endereços privados, loopback, link-local,
multicast, reservados e formas IPv6 de tradução/túnel são bloqueados.
Cada redirecionamento é validado; são permitidos até cinco saltos. O backend
valida todos os endereços retornados pelo DNS antes de conectar ao IP público
canônico, preservando Host, SNI e validação TLS. Uma nova conexão resolve e
valida novamente; a conexão já aberta permanece ligada ao IP validado.

Proxies e certificados definidos implicitamente pelo ambiente não são usados
na coleta. Não há opção de desativar a política por cadastro. Sites próprios
públicos com embed Greenhouse continuam permitidos. `unsafe_target` indica
bloqueio de segurança, sem tentativa de acesso ao destino rejeitado.

Firewall de saída do worker e limites de recursos são defesas adicionais;
configuração de código não comprova a política da máquina em execução.
Os relatórios detalhados da auditoria permanecem privados fora do Git.

## Limites durante a leitura

O worker declara usuário 10001, filesystem e código montado somente leitura,
tmpfs limitado em /tmp, sem capabilities, sem ganho de privilégios, com teto
de memória de 1 GiB e 256 processos. O navegador instalado tem caminho de
leitura compartilhado, independente do home do root. `.dockerignore` permite
somente código/manifests necessários; `.env`, venv, dados e logs não integram
o contexto de build. O worker recebe somente as conexões locais explícitas
do Compose, sem carregar todas as variáveis do `.env` da API.

Isso não é firewall de saída nem sandbox comprovado: Docker inativo impediu
build/execução local. Validar a imagem e permissão de leitura do bind mount
na implantação antes de substituir um worker. Redis continua sendo uma
fronteira de confiança: não expor a terceiros; o worker executa tarefas da
fila. Rotação de credenciais e alterações na infraestrutura real não foram
realizadas. O uso de Playwright em novos adaptadores exige validação própria.

Compose validado com `docker compose --profile worker config --quiet`, sem
iniciar serviços. A verificação estática também impede USER root/ausente no
Dockerfile. Build e execução continuam pendentes enquanto Docker não estiver ativo.

O coletor recebe dados em streaming: limite de 10 MiB tanto para bytes de
transporte quanto para o corpo descomprimido, antes de interpretar HTML/JSON.
Content-Length acima do teto é recusado sem ler o corpo; a contagem funciona
também sem esse cabeçalho. Corpos de redirecionamento não são baixados.

Solicitamos `Accept-Encoding: identity`. Gzip também é aceito com saída
incremental limitada; gzip truncado/concatenado e outras codificações são
recusados. Nunca usar iter_bytes como única proteção contra expansão:
a descompressão automática pode alocar o corpo antes da verificação.

O orçamento de 180 segundos por fonte inclui rede, redirects e retries;
timeouts de socket diminuem conforme o tempo restante. A espera de DNS é
limitada e há no máximo duas resoluções em segundo plano; o resolvedor nativo
que exceder o prazo pode terminar depois, sem autorizar conexão ao destino.
O timeout de job do RQ continua como proteção adicional. Limites são
aplicados também na validação de portal, que reutiliza o coletor.

Verificação da proteção de rede: 43 testes de rede/coleta/validação passaram
em cópia temporária sem `.env`, com resolução/conexões externas e acesso à
infraestrutura real bloqueados. Ruff e verificação de whitespace passaram.
Isso não demonstra a configuração de uma implantação nem substitui testes
controlados após atualizar o worker.

Após adicionar streaming, limites de expansão e orçamento de rede, os 88
testes do backend passaram no mesmo isolamento, incluindo feeds pequenos,
gzip legítimo, expansão excessiva, fluxo lento e fechamento antecipado.
Ruff e `git diff --check` também passaram. O aviso de depreciação do TestClient
do Starlette é conhecido; nenhuma troca de cliente/framework foi feita.
