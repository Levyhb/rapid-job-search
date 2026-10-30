# Segurança do ambiente local

O RapidJobSearch é um painel pessoal, sem contas ou isolamento entre usuários.
Mantenha API, frontend e bancos em loopback. Publicar o código não autoriza
hospedar a aplicação abertamente: autenticação, autorização e revisão de
origens/Host/CSRF são requisitos para uma futura hospedagem.

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
