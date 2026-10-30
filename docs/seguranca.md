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

Verificação da proteção de rede: 43 testes de rede/coleta/validação passaram
em cópia temporária sem `.env`, com resolução/conexões externas e acesso à
infraestrutura real bloqueados. Ruff e verificação de whitespace passaram.
Isso não demonstra a configuração de uma implantação nem substitui testes
controlados após atualizar o worker.
