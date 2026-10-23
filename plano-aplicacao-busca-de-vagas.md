# Plano de desenvolvimento — Busca de vagas em portais de empresas

Documento de contexto e requisitos para agentes de desenvolvimento. Versão inicial: 22 de outubro de 2026.

## 1. Intuito da aplicação

A aplicação será um painel pessoal para encontrar oportunidades de trabalho diretamente nos portais de carreira de empresas escolhidas pelo usuário. Seu objetivo é reduzir o trabalho de visitar repetidamente cada portal, navegar por suas páginas e procurar cargos de interesse.

O usuário fornecerá uma lista de empresas e os links de seus portais. Também cadastrará os cargos, termos e condições que deseja procurar. A aplicação consultará esses portais, percorrerá suas listagens e apresentará somente as vagas que atendam às regras configuradas.

A saída principal será uma tabela no formato **Empresa | Nome da vaga**, com o nome funcionando como link direto para a oportunidade. Informações adicionais poderão ajudar a filtrar e acompanhar os resultados, sem dificultar essa experiência principal.

Exemplo de necessidade atendida: “Quero procurar vagas de Engenheiro de Software e Desenvolvedor Full Stack Júnior nas empresas que acompanho, sem abrir manualmente dezenas de sites.”

## 2. Escopo e premissas

A primeira versão será voltada a um único usuário, com execução local e consultas iniciadas manualmente. A interface e as mensagens serão em português do Brasil. Os anúncios serão preservados no idioma original.

A stack aprovada pelo usuário é **Next.js no frontend, Python com FastAPI no backend, Playwright para Python na automação de navegador e PostgreSQL como banco de dados**. Os agentes deverão adotar essas tecnologias como premissas da implementação. Next.js fornecerá a interface de configuração e consulta; Python com FastAPI gerenciará os pedidos, as buscas e os resultados; Playwright navegará nos portais que exigirem um navegador; PostgreSQL armazenará empresas, perfis, vagas e histórico. Este plano define o comportamento do produto; a organização interna, as bibliotecas complementares e as instruções de implementação ficam para a definição da arquitetura.

As consultas demoradas aos portais deverão ser executadas em um processo de trabalho em segundo plano, permitindo que a interface acompanhe o progresso sem manter uma única requisição aberta durante toda a coleta. A tecnologia desse processamento também será definida na arquitetura. APIs públicas e leitura direta de páginas continuam sendo alternativas à automação de navegador, conforme cada fonte.

O produto não depende de IA para cumprir seu objetivo inicial. A filtragem deverá ser explicável, com regras que o usuário consiga visualizar e ajustar.

**Incluído na primeira versão:**

- Cadastro e importação de empresas e portais.
- Cadastro de perfis de busca, termos, variações e exclusões.
- Consulta das fontes suportadas, incluindo suas páginas e mecanismos de carregamento progressivo.
- Filtragem, deduplicação e persistência dos resultados.
- Acompanhamento de progresso, falhas e cobertura de cada consulta.
- Visualização das vagas com links diretos, histórico e exportação.

**Fora do escopo desta etapa:**

- Leitura de currículo, avaliação de compatibilidade e pontuação de match com ATS.
- Candidatura automática, preenchimento de formulários ou envio de mensagens.
- Descoberta automática de novas empresas fora da lista cadastrada.
- Busca geral em toda a internet ou cobertura garantida de qualquer portal.
- Acesso automático a áreas privadas que exijam credenciais de candidato.
- Gestão de múltiplos usuários, assinaturas e cobrança.

Agendamento e notificações externas serão evoluções posteriores. A primeira versão deverá entregar valor com o botão “Buscar agora”.

## 3. Jornada principal do usuário

1. O usuário cadastra ou importa empresas com seus respectivos portais.
2. Cria um perfil de busca, como “Desenvolvimento — Júnior”.
3. Adiciona os cargos de interesse e suas variações, escolhe exclusões e define filtros opcionais.
4. Seleciona as empresas que participarão da consulta.
5. Confere um resumo da configuração e inicia a execução.
6. Acompanha o andamento por empresa e vê resultados parciais identificados como provisórios.
7. Recebe a tabela final de vagas encontradas e o resumo das fontes consultadas.
8. Abre a oportunidade no portal original, favorita ou ignora resultados e exporta a lista quando desejar.
9. Em uma consulta posterior, identifica quais vagas são novas, quais continuam presentes e quais deixaram de ser encontradas.

Uma consulta deverá continuar sendo processada se o usuário navegar para outra tela da aplicação. Como a execução é local, o encerramento do processo ou do computador interromperá o trabalho; essa interrupção deverá ser registrada quando o sistema voltar.

## 4. Cadastro de empresas e portais

Cada empresa deverá ter nome, um ou mais endereços de portais, situação ativa/inativa e observações opcionais. Permitir mais de um portal atende empresas que separam vagas por país, unidade ou marca.

O usuário poderá inserir dados individualmente ou colar uma lista no formato **Nome da empresa | Link do portal**. Também deverá ser possível importar uma lista tabular e revisar os dados antes de confirmar.

A importação deverá identificar linhas incompletas, endereços inválidos e possíveis duplicatas. Linhas com problema não poderão desaparecer silenciosamente. O usuário deverá conseguir corrigir os itens ou importar apenas as linhas válidas.

Quando um link levar a uma página institucional, a aplicação deverá tentar localizar o acesso claramente identificado ao portal de carreiras. Ao encontrar múltiplas opções ambíguas, deverá pedir a correção ou seleção do endereço, em vez de escolher uma origem sem explicar.

Cada portal deverá exibir a última consulta, o último sucesso e sua situação de suporte. Uma empresa conhecida não significa que seu portal esteja automaticamente suportado.

Desativar uma empresa a retirará das próximas buscas, preservando os resultados e o histórico anteriores.

## 5. Perfis de busca e significado dos termos

Um perfil reunirá as regras de uma intenção de busca. Exemplos: “Full Stack Júnior”, “Engenharia de Software” e “Backend remoto”. O usuário poderá criar vários perfis e escolher quais executar.

Cada perfil conterá:

- Nome e empresas participantes, com a opção de usar todas as empresas ativas.
- Grupos de cargos desejados e suas variações aceitas.
- Termos de exclusão.
- Preferências opcionais de senioridade, localidade e modalidade de trabalho.
- Política para anúncios que não informem algum dos campos exigidos.

**Regra entre cargos:** basta corresponder a um dos grupos de cargos cadastrados. Procurar “Engenheiro de Software” e “Desenvolvedor Full Stack” significa aceitar qualquer um dos dois, sem exigir ambos no anúncio.

**Regra dentro de um cargo:** o usuário poderá cadastrar variações equivalentes. Por exemplo, o grupo “Desenvolvedor Full Stack” poderá conter “Desenvolvedor Fullstack”, “Full Stack Developer” e “Full-Stack Developer”. Essas equivalências serão visíveis e editáveis. Não haverá tradução ou expansão de sinônimos oculta.

**Normalização:** diferenças de maiúsculas, acentos, espaçamento e pontuação simples não deverão impedir correspondências. Termos curtos deverão respeitar limites de palavras; “Java” não deverá corresponder automaticamente a “JavaScript”.

**Escopo da correspondência:** por padrão, os termos de cargo serão procurados no título. Menções ao cargo no corpo do texto não bastarão para incluir uma vaga de outra função. Uma opção explícita poderá ampliar a busca para título e descrição, indicando que isso pode trazer resultados mais amplos.

**Exclusões:** termos de exclusão se aplicarão ao título por padrão. Assim, mencionar colaboração com profissionais seniores na descrição não excluirá indevidamente uma vaga júnior. Quando houver correspondência com uma exclusão no escopo configurado, a exclusão terá prioridade sobre a inclusão.

Expressões compostas serão avaliadas como frases ou variações cadastradas, não como palavras soltas em qualquer posição. “Engenheiro de Software” não deverá incluir “Engenheiro Civil” apenas por compartilhar a palavra “Engenheiro”.

## 6. Senioridade, localidade e modalidade

A senioridade deverá ser um filtro separado do cargo, mesmo quando o usuário inicialmente digitar uma expressão como “Desenvolvedor Full Stack Jr”. A interface poderá sugerir a separação em cargo e nível, mantendo a interpretação visível e editável.

As equivalências de nível deverão ser explícitas, por exemplo “Jr”, “Júnior” e “Junior”. Rótulos ambíguos, como “I” ou “Associate”, não serão classificados automaticamente sem uma regra validada para a fonte.

Filtros diferentes serão combinados: uma vaga deverá atender a um cargo desejado e aos demais critérios obrigatórios do perfil. Múltiplas opções dentro do mesmo filtro serão alternativas aceitas, como “Júnior ou Pleno”.

Para campos ausentes, haverá duas políticas:

- **Flexível, padrão:** manter a vaga e sinalizar “não informado — verificar”.
- **Estrita:** exigir evidência de atendimento ao filtro e excluir o anúncio quando ela não existir.

Se houver um valor conhecido que contradiga o filtro, a vaga será excluída em ambas as políticas. A opção flexível serve apenas para informação ausente ou inconclusiva.

“Remoto” não implica disponibilidade mundial. Uma vaga remota limitada ao Brasil deverá preservar essa restrição. A aplicação não deverá inferir cidade, país ou nível a partir de suposições sobre a empresa.

Quando uma listagem não trouxer as informações necessárias, a ferramenta deverá consultar a página de detalhes dos anúncios candidatos antes de decidir. Se a leitura falhar, o resultado ficará pendente de verificação ou seguirá a política explícita para informação desconhecida.

### Exemplos de comportamento esperado

Considerando o grupo “Desenvolvedor Full Stack”, com variações em inglês cadastradas, filtro Júnior e política flexível:

| Anúncio | Resultado esperado |
|---|---|
| Desenvolvedor Full Stack Jr | Incluir: cargo e nível atendidos |
| Junior Full-Stack Developer | Incluir: variação cadastrada e nível atendido |
| Desenvolvedor Fullstack | Consultar detalhes; se o nível continuar ausente, incluir com aviso |
| Desenvolvedor Full Stack Sênior | Excluir: nível incompatível |
| Analista de Suporte com menção a full stack na descrição | Excluir na busca padrão por título |
| Desenvolvedor Backend Jr | Excluir se Backend não estiver em outro grupo aceito |

Cada vaga incluída deverá informar qual grupo correspondeu e quais filtros foram atendidos ou ficaram sem informação.

## 7. Consulta dos portais e navegação página por página

A aplicação deverá escolher a forma de coleta adequada a cada portal. Poderá usar dados públicos estruturados, ler a listagem ou navegar pela interface, conforme a fonte suportada.

“Percorrer página por página” significa cobrir toda a listagem relevante. Em um portal com páginas numeradas, isso significa avançar até a última. Em outros, significa consumir os lotes de dados, acionar “carregar mais” ou continuar a rolagem até o fim. Não é obrigatório abrir visualmente cada página quando a mesma informação estiver disponível de forma estruturada e confiável.

A coleta deverá contemplar:

- Paginação por números ou botões de próxima página.
- Carregamento por lotes, “ver mais” ou rolagem contínua.
- Portais que redirecionam para um fornecedor de recrutamento.
- Listagens resumidas que exigem abrir o anúncio para obter filtros ou o endereço direto.

Filtros de pesquisa do próprio portal só deverão reduzir o universo consultado quando seu comportamento tiver sido validado. Um filtro local por “Jr” não poderá eliminar silenciosamente anúncios escritos como “Junior”. A busca ampla com filtragem na aplicação será a referência quando não houver essa garantia.

O encerramento normal ocorrerá ao confirmar que não há próxima página ou novos lotes e que os dados esperados foram processados. A ausência de novos itens repetida poderá indicar travamento; nesse caso, a consulta será marcada como parcial se o fim não puder ser confirmado.

Deverão existir limites de duração, páginas e tentativas para impedir execuções intermináveis. Atingir um limite deverá gerar estado **parcial**, com motivo e indicação de até onde foi possível consultar. Nunca equivalerá a uma consulta completa.

O painel deverá mostrar páginas ou lotes processados e quantidades de vagas examinadas e aceitas. Uma porcentagem só deverá aparecer quando o total for conhecido.

## 8. Compatibilidade, bloqueios e falhas

Os portais deverão ter uma classificação de suporte: validado, parcial, não suportado, indisponível ou requer ação do usuário. Essa classificação deverá ser separada do resultado de uma execução específica.

Quando houver bloqueio, desafio de verificação, exigência de login ou falha persistente, o sistema deverá registrar o motivo, preservar os resultados já obtidos e continuar nas outras empresas. Poderá oferecer uma fonte pública alternativa ou orientar uma verificação manual.

O produto não deverá depender de uma promessa de superar qualquer proteção antibot. A cobertura real será definida por testes com a lista do usuário. Consultas deverão ter frequência controlada, tentativas limitadas e respeito aos limites de acesso das fontes.

Uma resposta tecnicamente recebida não prova que a listagem foi lida: a aplicação deverá distinguir página de vagas, tela de erro, desafio e página vazia legítima.

Estados por portal e execução:

| Estado | Significado |
|---|---|
| Aguardando | Ainda não começou |
| Consultando | Coleta em andamento |
| Concluída | A listagem prevista foi percorrida e processada |
| Parcial | Parte da consulta ficou incompleta |
| Bloqueada | Uma barreira de acesso impediu a coleta |
| Falhou | Um erro impediu a consulta |
| Não suportada | O formato ainda não tem um mecanismo validado |
| Cancelada ou interrompida | A execução terminou antes de completar |

“Nenhuma vaga compatível” será um resultado de uma consulta concluída, não um substituto para bloqueio ou falha.

## 9. Resultados e organização das vagas

A tela de resultados deverá destacar a tabela **Empresa | Nome da vaga**, com link direto para o anúncio original. O clique abrirá a oportunidade em outra aba.

Colunas ou detalhes adicionais poderão mostrar localidade, modalidade, senioridade, perfil correspondente, primeira identificação e última confirmação. A data de descoberta pela aplicação deverá ser distinta da data de publicação informada pelo portal.

O usuário poderá filtrar por empresa, perfil, vaga nova, favorita e ignorada. A ordenação padrão será pelas descobertas mais recentes; também haverá ordenação por empresa e título.

Favoritar e ignorar serão ações pessoais persistentes e reversíveis. Ignorar uma vaga apenas a ocultará da visualização padrão; não mudará sua situação na fonte.

A exportação deverá refletir os filtros selecionados e conter, no mínimo, empresa, título e endereço completo. No painel, o título será clicável; no arquivo exportado, o endereço deverá continuar utilizável fora da aplicação.

Resultados históricos deverão ser distinguíveis dos confirmados na consulta atual. Uma consulta incompleta não poderá fazer uma vaga antiga parecer recém-verificada.

## 10. Identidade, duplicatas e ciclo de vida

Uma vaga será identificada preferencialmente pelo identificador estável da fonte. Na ausência dele, será usado o endereço do anúncio tratado de forma conservadora. Parâmetros de rastreamento poderão ser descartados, mas parâmetros necessários para identificar a vaga deverão ser preservados.

O mesmo anúncio encontrado em páginas diferentes, em múltiplos perfis ou em portais duplicados não deverá gerar várias linhas. A vaga única poderá registrar todos os perfis que a aceitaram.

Vagas com o mesmo título poderão ser diferentes. Localidade, identificador e origem deverão ser considerados antes de qualquer consolidação. Possíveis duplicatas entre fontes diferentes não deverão ser mescladas apenas por semelhança textual.

Cada vaga deverá distinguir:

- **Nova para o usuário:** primeira descoberta pela aplicação.
- **Presente:** reencontrada em uma consulta válida.
- **Não reencontrada:** ausente em uma nova consulta completa e comparável.
- **Encerrada:** a fonte apresenta evidência explícita de encerramento.
- **Situação desconhecida:** não há confirmação recente devido a falha ou cobertura insuficiente.

Uma única ausência não deverá ser apresentada como prova de encerramento. Consultas parciais, bloqueios, mudanças de perfil e alterações de filtros não poderão encerrar vagas automaticamente.

Quando uma vaga deixar de corresponder a um perfil, isso mudará sua associação ao perfil, sem afirmar que desapareceu do portal. Se reaparecer com a mesma identidade, o histórico será preservado. Uma republicação com novo identificador poderá ser tratada como nova, com vínculo histórico quando houver evidência suficiente.

## 11. Execuções, histórico e rastreabilidade

Cada execução deverá guardar a configuração usada no momento do início: empresas, perfis, termos e filtros. Alterações feitas enquanto uma consulta estiver em andamento só valerão para execuções futuras.

O histórico deverá mostrar início, término, duração, situação geral e resultados por empresa. Uma execução poderá terminar com parte das fontes concluídas e parte bloqueadas, sem perder as vagas válidas.

Será possível cancelar a consulta e repetir somente as fontes com problema. A repetição deverá ser identificável e não duplicar vagas. Consultas simultâneas ao mesmo portal deverão ser coordenadas para evitar trabalho repetido e resultados conflitantes.

Para cada resultado, será necessário saber qual fonte o forneceu, quando foi consultado e por que passou no filtro. Os diagnósticos deverão distinguir falha de navegação, falha de interpretação e ausência real de correspondências.

O histórico terá configurações suficientes para explicar diferenças entre buscas. A retenção de páginas completas e descrições integrais deverá ser limitada ao necessário para o produto e para diagnóstico.

## 12. Experiência das telas

**Visão inicial:** resumo das empresas ativas, perfis disponíveis, última consulta e vagas novas. A ação principal será iniciar uma busca.

**Empresas:** cadastrar, editar, importar, ativar/desativar e verificar portais. Deverá deixar claros os itens ainda não validados.

**Perfis:** configurar cargos e variações, exclusões e filtros. Uma área de prévia deverá permitir testar um título e informações complementares para entender se a regra o aceitaria e por quê.

**Execução:** acompanhar fontes, páginas ou lotes processados, resultados provisórios e erros. Deverá permitir cancelamento e manter a navegação da aplicação disponível.

**Vagas:** consultar a tabela, aplicar filtros, abrir anúncios, favoritar, ignorar e exportar.

**Histórico:** revisar execuções anteriores e repetir fontes com problema.

Estados vazios deverão orientar a próxima ação: cadastrar empresas, criar perfil, iniciar consulta ou ajustar regras. Mensagens como “zero vagas” deverão vir acompanhadas da cobertura obtida.

## 13. Qualidade e critérios gerais de aceite

O produto estará apto para uso inicial quando conseguir demonstrar:

1. Importação de uma lista de empresas com revisão de erros e duplicatas.
2. Perfis com alternativas de cargos, variações, exclusões e filtros compreensíveis.
3. Regras aprovadas nos exemplos deste documento, inclusive campos ausentes e títulos semelhantes.
4. Coleta de uma vaga compatível que esteja além da primeira página de um portal suportado.
5. Encerramento correto da paginação e identificação explícita de coleta parcial.
6. Links diretos válidos nas vagas apresentadas.
7. Uma linha por anúncio, mesmo quando encontrado por vários perfis.
8. Falha de uma empresa sem interrupção indevida das demais.
9. Distinção entre ausência de resultados, bloqueio e portal não suportado.
10. Persistência dos dados e identificação de vagas novas em uma segunda consulta.
11. Preservação do histórico quando uma vaga for ignorada, deixar de corresponder a um perfil ou não puder ser consultada.
12. Exportação consistente com a tabela e suas regras de filtragem.
13. Recuperação após interrupção, com estado verdadeiro da execução anterior.

A validação deverá combinar cenários controlados com portais reais representativos da lista do usuário. Os cenários controlados verificarão paginação, duplicatas, falhas e regras de filtragem de forma reproduzível. A inspeção manual de amostras reais verificará se títulos, links e cobertura correspondem ao portal.

Também deverão ser avaliadas vagas que o sistema descartou, para detectar oportunidades perdidas por regras excessivamente restritivas. A qualidade será medida tanto pelos resultados indevidos quanto pelas vagas relevantes omitidas.

## 14. Etapas de desenvolvimento e entregáveis

### Etapa 1 — Validar as fontes e as regras

Usar uma amostra representativa da lista de empresas para identificar tipos de portal, paginação, disponibilidade de dados e barreiras. Consolidar exemplos de títulos que o usuário quer aceitar e rejeitar.

**Entregáveis:** matriz de suporte por portal, perfis de exemplo, casos de aceite e limites conhecidos. A matriz deverá informar quais fontes são viáveis para a primeira entrega e quais precisam de investigação adicional.

### Etapa 2 — Construir o fluxo de configuração

Entregar cadastro e importação de empresas, perfis de busca e prévia das regras. O usuário deverá conseguir preparar uma consulta completa antes de depender de integrações com todos os portais.

**Entregáveis:** experiência de configuração funcional e persistente, com validação de dados e regras de filtragem verificadas.

### Etapa 3 — Entregar uma consulta completa em uma fonte validada

Implementar o percurso integral: configuração, execução, paginação, leitura dos dados necessários, filtragem, persistência e resultado clicável. Incluir tratamento real de falhas e estados parciais desde esta etapa.

**Entregáveis:** uma experiência utilizável de ponta a ponta, validada com vaga localizada além da primeira página.

### Etapa 4 — Ampliar a cobertura

Adicionar os demais tipos de portal priorizados. Fontes com o mesmo fornecedor poderão compartilhar comportamento, mas cada portal deverá ser verificado antes de receber a classificação de validado.

**Entregáveis:** matriz de cobertura atualizada, consultas independentes por empresa e diagnósticos claros para fontes ainda não suportadas.

### Etapa 5 — Consolidar o uso recorrente

Completar histórico, comparação entre consultas, deduplicação entre perfis, favoritos, ignorados, exportação e recuperação de interrupções.

**Entregáveis:** primeira versão pronta para uso pessoal recorrente, acompanhada de instruções de execução local e limitações verificadas.

### Evoluções posteriores

Agendamento, alertas de novas vagas, expansão de fontes e filtros adicionais poderão ser priorizados com base no uso. A análise de currículo e o match com vagas constituirão um módulo futuro, fora dos critérios de conclusão deste plano.

## 15. Divisão de responsabilidades para agentes

Esta divisão orienta a distribuição futura do trabalho. Não determina bibliotecas, arquivos ou detalhes de código.

| Frente | Responsabilidade | Dependência principal |
|---|---|---|
| Produto e experiência | Jornadas, telas, mensagens e regras visíveis | Requisitos e exemplos de aceite |
| Configuração e dados | Empresas, perfis, identidade das vagas e histórico | Definição compartilhada dos conceitos |
| Coleta de fontes | Acesso, paginação, detalhes e cobertura por portal | Matriz de suporte e formato comum dos resultados |
| Filtragem | Correspondências, exclusões, campos ausentes e justificativas | Semântica dos perfis e dados coletados |
| Execução | Progresso, cancelamento, limites, repetição e falhas | Estados e contratos acordados |
| Integração e qualidade | Fluxo completo, casos de aceite e verificação real | Entregas integradas das demais frentes |

Antes de dividir implementações, os agentes deverão concordar sobre o significado de empresa, portal, perfil, vaga, execução, correspondência e consulta completa. Também deverão definir o conjunto mínimo de informações trocadas entre coleta, filtragem e interface.

Cada frente deverá entregar seu comportamento verificado, limitações conhecidas e evidências de aceite. Um responsável pela integração deverá garantir que decisões locais não alterem silenciosamente as regras do produto.

Nenhum agente deverá substituir uma coleta real por dados fictícios em uma entrega apresentada como funcional. Dados demonstrativos poderão existir em um ambiente de demonstração claramente identificado.

## 16. Decisões pendentes e padrões iniciais

As decisões abaixo poderão ser refinadas sem impedir o desenho inicial:

| Tema | Padrão proposto | Informação necessária para refinar |
|---|---|---|
| Portais da primeira entrega | Priorizar tipos representativos da lista real | Amostra de empresas e endereços |
| Cargos iniciais | Engenharia de Software e Desenvolvimento Full Stack | Termos e variações aceitos pelo usuário |
| Senioridade | Configurável por perfil | Níveis que o usuário deseja considerar |
| Localidade e modalidade | Sem restrição até serem configuradas | Países, cidades e preferência de trabalho |
| Campos ausentes | Aceitar com aviso | Preferência por maior cobertura ou maior precisão |
| Periodicidade | Busca manual | Necessidade futura de agendamento |
| Escala e desempenho | Execução em segundo plano com progresso | Quantidade de portais e volume observado |

Não prometer um tempo total de consulta antes de medir a amostra real. A quantidade de empresas, o número de páginas e o comportamento dos portais influenciam esse tempo.

## 17. Definição de conclusão da primeira versão

A primeira versão estará concluída quando o usuário conseguir cadastrar suas empresas, definir os cargos que procura, iniciar uma consulta e receber uma lista persistente de vagas compatíveis com links diretos, acompanhada de uma indicação confiável de quais fontes foram completamente consultadas e quais ficaram pendentes.

O resultado deve permitir responder: **“Quais oportunidades com os termos que defini foram encontradas nas empresas que acompanho, e quão completa foi essa busca?”**

O valor do produto depende tanto de encontrar vagas relevantes quanto de comunicar corretamente a cobertura e as limitações de cada consulta.
