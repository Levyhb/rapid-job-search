# Segurança do ambiente local

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
