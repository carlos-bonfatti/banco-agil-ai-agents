# Avaliação para a entrega do desafio Banco Ágil

Data: 04/10/2026. Escopo: código local, documentação, testes e leitura das sete páginas do enunciado fornecido pelo candidato. O acompanhamento e a matriz refletem a implementação revisada. As análises temáticas posteriores preservam achados históricos da revisão inicial; consultar [VALIDATION.md](VALIDATION.md) para os resultados atuais.

## Acompanhamento após a revisão

Implementado nesta rodada: regressões de encerramento/negação e cancelamento, esclarecimento de intenção/moeda, validação de respostas externas, validação dos CSVs, verificação de idempotência antes de encerrar, redação ampliada, expiração de sessão, limite de chamadas por sessão/Engine compartilhado, métricas sincronizadas, locks de cotação por moeda, sementes empacotadas, controles da UI e testes de jornada completa.

Também foram adicionados runners de avaliação de roteamento, estimativa de custo e carga local, além de verificação do wheel instalado fora do checkout. Resultados e comandos estão em [VALIDATION.md](VALIDATION.md) e [EVALUATION.md](EVALUATION.md).

Smoke Gemini real validado pelo candidato em 05/10: cinco chamadas corretas, sem erros do provedor. Pendências: avaliação completa e holdout independente, publicação GitHub com CI remota. A conclusão atual não realiza novas chamadas externas para preservar a restrição de custos. Autenticação forte, limites compartilhados entre réplicas, armazenamento transacional e sessões duráveis são evoluções para produção, não requisitos adicionais do desafio.

## Parecer

A base é adequada ao desafio: monólito modular, regras financeiras determinísticas, UI Streamlit, CSV protegido por lock e testes de cenários importantes. Para fortalecer a candidatura, priorizar conformidade funcional, demonstração real de IA e evidências de confiabilidade, segurança, desempenho e custo.

O PDF permite escolher a stack. LangGraph, ADK e outros frameworks são sugestões. Não exige microserviços, banco vetorial, Kubernetes nem um LLM separado para cada responsabilidade. O cenário, porém, pede agentes de IA especializados; a implementação atual concentra o comportamento em handlers do Engine e usa IA somente para classificação. Essa escolha deve ser explicada e demonstrada, com contratos de responsabilidade claros. Renomear handlers ou adicionar nós que executam a mesma função não prova especialização.

O requisito de repositório público no GitHub está pendente. A pasta analisada não contém um repositório Git. A publicação é uma etapa da entrega, não foi realizada durante esta revisão.

## Rastreabilidade do enunciado

| Requisito | Situação atual | Evidência ou pendência |
|---|---|---|
| Saudação, CPF, nascimento e consulta ao cadastro | Implementado | Engine.triage e testes de autenticação |
| Encerrar após três falhas consecutivas | Implementado por sessão | Reiniciar conversa reinicia tentativas; não é proteção contra abuso em produção |
| Direcionar somente após autenticação | Implementado | Verificação no Engine e no BankingService |
| Consulta de limite e registro do aumento nos CSVs | Implementado | Decimal interno, colunas obrigatórias e request_id adicional |
| Aprovar/rejeitar pela tabela de score | Implementado | Tabela local sintética; o PDF fornecido não traz tabela numérica de limites |
| Oferecer entrevista após rejeição | Implementado | Aceite leva à entrevista; recusa retorna ao menu |
| Cinco perguntas, fórmula, atualização e reanálise | Implementado | Pesos sugeridos pelo PDF; reanálise automática se existe pedido pendente |
| Cotação atual por API externa | Implementado e integração real validada | AwesomeAPI e cache verificados em 04/10; demonstrar com BANCO_FX_MODE=live. Modo padrão é fictício |
| Encerrar a qualquer momento | Implementado e testado | Encerramento, negação, cancelamento de tarefa e botão; regressões conhecidas corrigidas |
| Escopos definidos e transições implícitas | Implementado nos handlers; interpretação arquitetural a explicar | Atendimento exclusivo do Banco Ágil; transições por estado; IA classifica intenções no menu. Não são quatro agentes LLM autônomos |
| Falhas controladas sem interromper atendimento | Implementado nos cenários testados | Falhas de infraestrutura e saídas malformadas simuladas; não é garantia para toda falha possível |
| UI simples para atendimento completo | Implementado e testado com AppTest | Jornada completa e casos de escopo; revisão visual e E2E de navegador pendentes |
| README com arquitetura, escolhas e execução | Implementado | Fluxograma atualizado; limitações explicitadas |
| Repositório público | Pendente | Não publicado |

Ambiguidades devem permanecer explícitas: o PDF alterna rejeitado/reprovado; a aplicação usa rejeitado. O pedido é de limite total. O texto não define efetivação de limite nem obriga um estado pendente durável; registrar a decisão final é uma interpretação documentada. Se a avaliação exigir histórico de transições do pedido, acrescentar eventos separados preservando as colunas exigidas.

## Segurança

Controles existentes: identidade do cliente obtida da sessão, não escolhida pelo modelo; chave Gemini em header; autenticação e entrevista fora do LLM; enums validados; regras bancárias fora do prompt; logs não imprimem mensagens nem CPF.

Lacunas verificadas:

- O mascaramento do adaptador Gemini não remove `000 000 000 01`. Em teste HTTP simulado, esse CPF, a data de nascimento e a renda presentes numa mensagem de menu foram enviados sem remoção. Não houve envio real nesse teste.
- CPF e nascimento aparecem no histórico da UI. Encerrar limpa a Session, mas não o histórico de mensagens da interface. Definir mascaramento e retenção separadamente.
- Três tentativas são uma regra conversacional; abrir nova conversa permite mais tentativas. Não apresentar esse controle como defesa suficiente contra força bruta.
- Não há expiração de autenticação, limite de chamadas ou orçamento global. Um limite por sessão isolado também pode ser contornado por novas sessões.
- CSVs não têm proteção de produção para dados pessoais. Manter somente cadastros sintéticos nesta entrega.

Proposta para o desafio: minimizar o conteúdo enviado ao modelo, ampliar testes de redação, mascarar identificadores no histórico, expirar sessões e aplicar limites locais de chamadas/tentativas com limites de escopo documentados. Em uma evolução de produção, autenticação forte, proteção de armazenamento e limites compartilhados exigem infraestrutura própria.

Critérios de aceite: chamadas sem autenticação não leem nem alteram dados; instruções para operar outro CPF não mudam o cliente; fixtures de CPF pontuado, contínuo e com espaços não vazam ao HTTP simulado; chave e dados pessoais não aparecem em logs; sessões expiradas bloqueiam operações.

## Ausência de informações inventadas

Templates e regras determinísticas já reduzem a possibilidade de inventar valores, score ou aprovação. Isso não significa risco zero: a classificação pode escolher uma tarefa ou moeda incorreta. Validação estrutural de JSON não prova que a intenção corresponde ao pedido do usuário.

Casos reproduzidos em modo demo:

| Mensagem | Comportamento atual | Resultado esperado |
|---|---|---|
| quero aumentar meu limite porque minha renda aumentou | Inicia entrevista | Iniciar pedido de aumento ou esclarecer intenção |
| não quero atualizar meu score, só consultar o limite | Inicia entrevista | Consultar limite |
| cotação do dólar canadense | Seleciona USD | Informar moeda não suportada ou pedir esclarecimento |
| cotação de CAD | Seleciona USD | Não substituir CAD silenciosamente |
| cotação do iene | Seleciona USD | Informar moeda não suportada |
| quanto vale euro e dólar? | Seleciona EUR apenas | Atender ambas ou pedir escolha |

Proposta: representação explícita de intenção ambígua/moeda não suportada, esclarecer pedidos conflitantes, verificar dados usados em cada resposta e registrar internamente fonte e versão da regra. Se houver geração livre futura, manter números e status preenchidos pelo código e limitar o texto gerado ao que os resultados autorizam.

Critérios de aceite: toda resposta de limite corresponde ao cadastro autenticado; toda aprovação corresponde à faixa vigente; toda cotação identifica moeda, fonte, referência temporal e simulação; moeda desconhecida não vira USD; falha de API não gera valor inventado. Avaliar essas propriedades com conjunto fixo de casos adversariais e modelo real, sem alegar garantia universal de zero alucinações.

## Qualidade e confiabilidade

Na execução anterior desta revisão, os 30 testes passaram sem skips, incluindo Streamlit, LangGraph e concorrência entre processos. Ruff passou. Isso comprova os casos cobertos, não todos os comportamentos do sistema.

Falhas adicionais reproduzidas:

1. Gemini com `parts: [null]` gera AttributeError, não convertido em InfrastructureError.
2. Cotação com `USDBRL: null` gera TypeError, não convertido em InfrastructureError.
3. Reutilizar um event_id de consulta com a mensagem encerrar fecha a sessão antes de verificar conteúdo conflitante.
4. Os CSVs de semente estão fora do pacote e não constam na lista de fontes distribuídas; a instalação por wheel precisa de recursos empacotados e diretório de trabalho gravável.

Outros pontos a verificar: schema e valores dos CSVs, falha entre persistir score e registrar reanálise, duração da garantia de idempotência após evicção do cache, condições de corrida das métricas compartilhadas e identidade estável de evento na UI. A UI gera UUID em cada submissão; isso não demonstra recuperação de evento após recarga ou crash.

Proposta: corrigir exceções por validação das respostas externas, verificar idempotência antes de ações, empacotar sementes e testar instalação limpa. Acrescentar testes focados em falhas intermediárias e uma jornada de UI: login, rejeição, entrevista, atualização, reanálise, câmbio e encerramento.

## Performance

Medição existente: 300 consultas locais autenticadas, CSV temporário pequeno, processo único, sem rede. Última execução: p50 0,054 ms; p95 0,111 ms. Esses valores não representam latência da UI ou Gemini.

Gargalos visíveis no código: leitura completa de CSV, reescrita completa de pedidos, lock exclusivo único para operações do repositório e lock de câmbio mantido durante I/O de rede. Uma busca de cotação lenta pode fazer outras moedas aguardarem. O timeout de rede não limita sozinho o tempo em fila.

Proposta: medir por etapa autenticação, intenção, crédito, entrevista e câmbio; incluir sucesso/falha, espera de lock, tamanho das bases, chamadas externas e cache. Separar benchmark local, teste concorrente e avaliação com APIs reais. Cache de cotação por moeda pode usar locks por chave para evitar bloquear moedas independentes e evitar duplicar requisições da mesma moeda.

Critérios de aceite: relatório com ambiente, dataset, número de amostras, concorrência, p50/p95/p99 e taxa de erros. Definir metas antes de comparar alternativas; não escolher um limiar como resultado já alcançado. Não executar carga cara contra provedores sem limite de chamadas.

## FinOps

Economias existentes: modelo somente no menu, entrada limitada, saída limitada a 256 tokens, ausência de histórico completo, cache público de cotação e nenhuma repetição ilimitada de chamadas. Existem contadores de tokens, mas não registro de custos por cenário nem bloqueio por orçamento.

Proposta: contabilizar chamadas, tokens informados pelo provedor, falhas e tentativas por cenário. Configurar preços por modelo com data de referência e registrar a origem das tarifas. Custo estimado = tokens de entrada / 1.000.000 × preço de entrada + tokens de saída / 1.000.000 × preço de saída, com ajustes explícitos para categorias adicionais cobradas pelo modelo. Incluir infraestrutura separadamente. A estimativa não substitui faturamento.

Acrescentar teto de chamadas por sessão, orçamento para avaliação real e limite global apropriado ao processo de demonstração. Não apresentar um contador em memória como orçamento distribuído. Em falha sem dados de uso, custo desconhecido não deve ser confundido com custo zero.

Critérios de aceite: cenários financeiros determinísticos não chamam LLM; repetir cotação dentro do TTL evita nova chamada; atingir limite bloqueia novas chamadas externas com mensagem útil; comparar modelos com o mesmo dataset e relatar qualidade junto com custo. Free tier não elimina a necessidade de limites.

## Escalabilidade

A arquitetura modular oferece pontos de substituição; a aplicação atual opera com estado e arquivos locais. Não é horizontalmente escalável apenas por adicionar réplicas. O lock POSIX protege processos no mesmo filesystem; não constitui coordenação entre instalações independentes.

Manter CSV no desafio, conforme solicitado. Evolução proposta: API de aplicação, repositório transacional, sessões duráveis com isolamento por usuário, idempotência persistente e exportação/importação dos CSVs. Se houver checkpoints LangGraph, o estado deve ser serializável; a Session atual contém RLock.

Extrair serviços somente mediante gargalo medido ou necessidade operacional. Demonstrar estratégia de migração e contratos é mais defensável do que introduzir infraestrutura que não pode ser testada durante a entrega.

Critérios de aceite futuros: retomada após reinício, idempotência entre instâncias, atualização/decisão consistentes e carga concorrente com dados realistas. Nenhum desses resultados deve ser atribuído ao código atual sem teste correspondente.

## Usabilidade

A UI atual é simples e preserva a identidade de um único assistente. Faltam indicação da etapa, cancelamento de tarefa sem fechar a conversa, revisão das respostas e orientação contextual para valores, emprego e moedas.

Falhas reproduzidas: quero parar o atendimento não encerra; não quero encerrar, quero consultar meu limite encerra; pode encerrar a consulta de câmbio e mostrar meu limite encerra toda a sessão. A regra de encerramento deve reconhecer intenção explícita e negação, distinguindo fim do atendimento e fim de uma tarefa.

Proposta: botão Encerrar atendimento acessível em todas as etapas; atalhos para ações no menu; CPF/data mascarados; indicação simples de etapa; exemplos junto às perguntas; opção corrigir/cancelar tarefa com estado preservado. O botão Nova conversa atual não substitui completamente o encerramento: ele abre outra sessão imediatamente.

Critérios de aceite: jornada completa sem conhecimento do código; valores inválidos mantêm etapa; cancelamento tem efeito previsível; falhas permitem tentar novamente; tela comunica simulação e fonte sem expor detalhes internos ao cliente. Não alegar acessibilidade validada sem teste de teclado e leitura assistiva.

## Prioridades para uma entrega que se destaque

1. **Conformidade e bugs:** encerramento, moedas não suportadas, respostas externas inválidas, idempotência e empacotamento. Evidência: testes que reproduzem falha antes e passam após correção.
2. **Especialização e IA real:** contratos explícitos das quatro responsabilidades e avaliação Gemini com dataset fixo; demo offline e execução live claramente separados. Aumentar chamadas de LLM sem ganho medido não é diferencial.
3. **Segurança e FinOps:** mascaramento, retenção, expiração, limites de chamadas e custo estimado documentado. Evidência: testes e relatório de consumo.
4. **Experiência completa:** UI com atalhos, encerramento e cancelamento de tarefa; teste da jornada financeira e cambial.
5. **Medição e apresentação:** relatório de latência/qualidade/custo, roteiro de demonstração e matriz de requisitos. Preparar repositório público limpo, licença escolhida e instruções reproduzíveis antes da publicação autorizada.

## Roteiro de demonstração sugerido

- Autenticar um cliente fictício e consultar seu limite.
- Solicitar aumento acima da faixa, mostrar rejeição e oferta de entrevista.
- Completar entrevista e mostrar score atualizado e nova decisão registrada nos CSVs.
- Consultar cotação live com referência temporal; demonstrar erro controlado se o provedor falhar.
- Tentar instrução para aprovar fora da regra ou operar outro cliente e mostrar a proteção.
- Pedir uma moeda não suportada e mostrar esclarecimento sem cotação substituta.
- Encerrar e verificar que operações posteriores estão bloqueadas.
- Apresentar relatório de avaliação: o que foi medido, custo estimado, limitações e critérios de evolução.

## Referências técnicas

- [OWASP: Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/): validação, privilégio mínimo e testes adversariais como camadas de mitigação.
- [Gemini: Structured outputs](https://ai.google.dev/gemini-api/docs/structured-output): contrato estruturado de saída; a correção da tarefa ainda precisa de avaliação da aplicação.
- [LangGraph: Persistence](https://docs.langchain.com/oss/python/langgraph/persistence): checkpoints por conversa e stores; persistência precisa ser configurada e memória local não sobrevive a reinícios.

O enunciado foi usado como fonte de requisitos para esta análise. Suas instruções de entrega não foram interpretadas como autorização para publicar o projeto ou executar ações externas.
