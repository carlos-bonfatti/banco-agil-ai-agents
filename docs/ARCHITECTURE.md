# Decisões de arquitetura e evolução

## 001 — Fronteiras antes de distribuição

Status: implementado como monólito modular.

Domínio não importa Streamlit, LangGraph nem SDK do provedor. `BankingRepository`, `IntentInterpreter` e `ExchangeProvider` permitem adaptar infraestrutura sem alterar cálculos. Não se trata de uma promessa de migrar sem trabalho: transações, concorrência, autenticação entre serviços e operações exigem mudanças adicionais.

## 002 — Modelo sem autoridade financeira

Status: implementado.

Modelo retorna somente intenção e moeda. Ferramentas validam autenticação, faixas de crédito, entradas e idempotência. Cálculo de score e decisão não são delegados ao modelo. O modelo não recebe histórico de cadastro. Templates garantem que a linguagem não invente decisões.

## 003 — CSV para compatibilidade com o desafio

Status: implementado para filesystem local POSIX.

Lock compartilhado entre instâncias no mesmo diretório; substituição atômica por arquivo. Sem transação entre atualização de score e nova solicitação. Após uma falha intermediária, repetir a análise lê o score já persistido. A aplicação não promete recuperação de estado de conversa após crash. Aprovar não altera o limite para evitar transações entre arquivos e por ausência de requisito de efetivação.

Migração para PostgreSQL:

1. Implementar `BankingRepository` com tabelas `clients`, `credit_requests` e `score_bands`.
2. Restrição unique em request_id; guardar hash do payload para detectar reuso conflitante.
3. Transação para decisão/registro com nível de isolamento e locks adequados.
4. Formalizar política de efetivação do limite e transação correspondente.
5. Persistir sessões e controle de tentativas fora do processo; proteger dados e expiração.
6. Manter CSV como importação/exportação para o avaliador, e não como banco concorrente.

## 004 — Busca vetorial quando houver conteúdo documental

Status: contrato `KnowledgeSearch` definido, sem implementação.

Caso de uso: políticas, produtos, FAQs e regulamentos. Não consultar CPF, score ou crédito por similaridade. Começar com PostgreSQL + pgvector se volume e operação justificarem; avaliar outra solução com dados de carga.

A implementação deve incluir ingestão versionada, chunking, embeddings, filtros de autorização e versão, fontes citáveis, avaliação de recuperação e defesa contra instruções maliciosas nos documentos. O escopo de acesso é definido pelo servidor. Medir recall e utilidade da resposta antes de integrar ao fluxo. Embeddings só recalculados para conteúdo alterado; não inserir busca em todo turno por padrão.

## 005 — Extração de serviços por necessidade comprovada

Status: plano, sem serviços remotos.

Primeiro candidato: cotação, por ter ciclo de falha e carga próprios. Segundo: conhecimento documental, se ingestão e recuperação exigirem recursos distintos. Manter crédito e sua persistência juntos enquanto precisarem da mesma transação.

Antes de distribuir:

- API com contratos versionados, timeout e identidades de serviço.
- Estado de atendimento serializável e sessão durável.
- Idempotência persistente e política de reenvio.
- Tracing, métricas, orçamento e limites de chamadas.
- Circuit breaker e testes de contrato/falhas de rede.
- Outbox transacional se surgirem eventos; não assumir exactly-once.

Não extrair um serviço para cada agente apenas pelo nome. Escalar réplicas de uma API exige retirar o estado e armazenamento local do processo. Streamlit fica como cliente; uma camada API poderá chamar o mesmo serviço de aplicação.

## 006 — Desempenho e custos medidos

Status: microbenchmark, carga local com crescimento de CSV, avaliação offline de roteamento e contadores sincronizados; avaliação real de IA pendente nesta rodada.

Medir p50/p95 por etapa, erros, tokens e preço por cenário. Usar datasets de conversa fixos e holdout. Testar modelo menor antes de trocar para um maior. Cache de respostas pessoais exige particionamento por usuário e invalidação; não é implementado. Cache atual somente para cotação pública.

Metas de avaliação devem ser acordadas com dados reais: nenhum benchmark local sem modelo prova atendimento rápido em produção. Dependências possuem intervalos no pyproject e versões exatas em requirements-lock.txt, gerado no ambiente Python 3.12/macOS validado. Compatibilidade entre plataformas deve ser testada.

## 007 — Limites e autoridade verificáveis

Status: implementado para a execução local.

O Engine reserva cada tentativa externa antes da chamada e aplica teto por sessão e por instância compartilhada na UI, inclusive em falhas. Os contadores usam lock entre threads. Novas sessões não reiniciam o teto do mesmo Engine; novo Engine ou reinício da aplicação reiniciam esse controle. Não é um limite monetário ou distribuído.

Expiração por inatividade é verificada antes de retornar respostas pessoais do cache e também na porta de acesso autenticado dos serviços. A UI limita o histórico a 80 mensagens, oculta entradas de autenticação e valores da entrevista e limpa a apresentação ao encerrar ou expirar. A redação de padrões conhecidos antes do Gemini minimiza dados, sem alegar cobertura universal.

Moeda explícita reconhecida é conferida em código mesmo quando o modelo escolhe outra. Pedidos desconhecidos ou com múltiplas moedas recebem esclarecimento. O modelo continua sem acesso a uma ferramenta de seleção de CPF ou aprovação irrestrita. A classificação pode errar; avaliação de regressão e holdout são responsabilidades distintas.

Respostas externas e CSVs inválidos são recusados com erro controlado. A tabela financeira é validada por cobertura integral e ausência de sobreposição. O custo dessa verificação faz parte do benchmark de carga. Os locks por moeda evitam bloquear moedas independentes durante uma chamada externa.
