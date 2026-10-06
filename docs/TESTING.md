# Estratégia e tipos de testes

Este documento explica o que verificamos, como reproduzir e o alcance de cada evidência. O registro da última execução está em [VALIDATION.md](VALIDATION.md). As propriedades de segurança e contexto estão em [SECURITY_AND_CONTEXT.md](SECURITY_AND_CONTEXT.md).

## Organização e classificação

A suíte utiliza `unittest` e `unittest.mock`, com CSVs em diretórios temporários. Gemini e falhas externas são simulados; os testes não exigem chave real. UI Streamlit e LangGraph são exercitados quando instalados e produzem skips quando seus extras estão ausentes.

As categorias abaixo se sobrepõem: um teste de integração pode também ser de segurança ou regressão. O total de 79 refere-se aos métodos de teste executados na última validação, não à soma de categorias ou de subcasos.

| Tipo | O que verifica | Exemplos existentes |
|---|---|---|
| Unitário | Funções e políticas isoladas | Formatos monetários, score/arredondamento, interpretação local, encerramento com negação e tarifas inválidas |
| Integração | Colaboração entre Engine, serviço e CSV | Autenticação, consulta, rejeição, entrevista, score persistido e reanálise |
| Segurança e isolamento | Fronteiras de identidade, dados e consumo | Operação sem autenticação, outro cliente, expiração, redação antes do HTTP e limite compartilhado |
| Regressão | Comportamentos que falharam durante a revisão | Negação encerrando conversa, renda confundida com entrevista, moeda desconhecida virando USD e event_id conflitante encerrando sessão |
| Falhas e recuperação | Erros externos ou de persistência sem perda indevida de fluxo | JSON malformado, cotação indisponível, CSV inválido, falha de `os.replace` e falha entre score persistido e reanálise |
| Concorrência | Proteção sob execução simultânea | Quatro processos preservando 16 pedidos, oito sessões competindo pelo teto do Engine e moedas independentes sem bloqueio mútuo |
| Idempotência | Reenvio sem repetir efeitos ou aceitar conteúdo conflitante | Mesma solicitação após reconstruir repositório, evento repetido e reanálise após falha |
| Integração de UI | Jornada pelo mecanismo de teste Streamlit | Login, aumento rejeitado, entrevista, reanálise, câmbio, cancelamento, encerramento e histórico limpo |
| Aderência ao escopo | Identidade, instituição, serviços disponíveis e ausência de efeitos indevidos | Receita, identidade Itaú, limite de outra instituição, serviços não implementados e referências legítimas a outros bancos |
| FinOps | Consumo e contabilização previsíveis | Reserva antes de chamada, falha consumindo tentativa, encerramento sem IA, tokens de pensamento e custo incompleto com uso desconhecido |
| Integração do grafo | Compatibilidade do adaptador LangGraph | Um turno de triagem chega ao Engine e retorna a pergunta esperada; não cobre checkpoints ou recuperação durável |

Arquivos:

- [test_bank.py](../tests/test_bank.py): 32 testes de domínio, fluxo, persistência, integrações e controles fundamentais.
- [test_regressions.py](../tests/test_regressions.py): 31 testes de regressão, expiração, consumo, privacidade, concorrência e jornada completa.
- [test_evaluation.py](../tests/test_evaluation.py): 5 testes do runner de avaliação e da estimativa de custo.
- [test_scope.py](../tests/test_scope.py): 8 testes de aderência ao escopo, com múltiplos subcasos, efeitos proibidos, recusas indevidas, Gemini simulado e interface.
- [test_presentation.py](../tests/test_presentation.py): 3 testes de saudação por horário, conversão UTC/Brasília e rejeição de timestamp sem fuso.

Esses números descrevem a versão validada em 04/10/2026; atualizar o registro quando a suíte mudar. Não foi medida cobertura de linhas/branches, portanto não há percentual de cobertura declarado.

## Execução da suíte e verificações estáticas

Na raiz do projeto, com ambiente virtual ativo:

```bash
python -m unittest discover -s tests -v
ruff check .
ruff format --check app.py banco_agil scripts tests
```

Na validação registrada, os 79 testes passaram sem skips, incluindo os extras. Ruff e formatação passaram. Lint e formatação verificam aspectos estáticos e consistência do código; não substituem testes de comportamento, análise de tipos ou auditoria de segurança.

## Aderência ao escopo do agente

O teste de escopo verifica comportamento e efeitos: identifica o Banco Ágil, não divulga valores de outras instituições, não inventa serviços e não executa ferramentas financeiras para pedidos recusados. Spies verificam ausência de chamadas a consulta de cliente, solicitação de crédito, atualização de score, cotação e interpretador nos casos resolvidos pela política local. Os CSVs também são comparados antes/depois.

A matriz inclui entradas com palavras de crédito dentro de pedidos fora do domínio, tentativa de mudar a identidade e perguntas com instituição desconhecida. Inclui controles contra recusa indevida: salário ou PIX originado no Itaú, boleto como motivo da consulta de limite e negação de consulta à outra instituição. Esses contextos não devem bloquear uma consulta ao Banco Ágil.

Os testes verificam também que o controle de escopo não substitui autenticação ou perguntas da entrevista; eventos preservam idempotência; respostas de escopo continuam disponíveis após limite de IA; e novas intenções Gemini são validadas e apresentadas por templates. São casos conhecidos e respostas HTTP simuladas, sem alegação de resistência universal a ataques.

## Interface: integração versus E2E

Temos testes de integração de interface com `streamlit.testing.v1.AppTest`: a jornada completa e os novos casos de escopo passam pela UI, com verificação de estado, resposta, ausência de exceções, controles e histórico. Os casos de escopo incluem retomada de uma consulta válida depois das recusas.

**Ainda não existe teste E2E em navegador real.** AppTest não exercita um navegador, renderização visual, transporte cliente-servidor ou acessibilidade. Não deve ser apresentado como E2E com browser. Nesta rodada, ampliamos a cobertura de AppTest sem instalar infraestrutura de automação de navegador ou acrescentar funcionalidades bancárias.

## Avaliação de roteamento e alucinação

```bash
python scripts/evaluate.py --mode demo --min-exact-match 1
```

O dataset [intents.json](../evaluation/intents.json) contém 54 exemplos conhecidos. O relatório [evaluation-demo.json](evaluation-demo.json) registra intenção/moeda, acerto exato, categorias, matriz de confusão, falhas, casos omitidos, latência e consumo. O gate opcional de acerto integral protege as regressões conhecidas do modo demo.

Essa avaliação é separada dos 79 testes. Não é um holdout independente, um benchmark do Gemini ou uma prova geral de ausência de alucinações. Os casos adversariais do dataset avaliam roteamento; autorização de cliente e crédito são verificadas nos testes do serviço/repositório. Não há métrica independente de geração factual livre, pois a implementação usa respostas controladas.

O modo `--mode gemini` foi preparado, mas não foi executado na rodada documentada. Ele usa API externa e pode gerar custo. Parâmetros de limites e estimativa estão em [EVALUATION.md](EVALUATION.md). Modelo, tarifas, erros e uso desconhecido devem acompanhar qualquer resultado real.

## Performance e carga

```bash
python scripts/benchmark.py
python scripts/benchmark_load.py
```

O microbenchmark executa 300 consultas autenticadas sem UI ou rede. A carga usa bases temporárias sintéticas, 2/1.000/10.000 clientes e pedidos iniciais, 1/4 threads e 40 amostras por cenário. São 12 cenários e 480 execuções na configuração padrão.

O relatório [performance-demo.json](performance-demo.json) registra latências e taxa de execução. A análise de gravação exclui login na latência, enquanto o throughput inclui a preparação de cada cenário. O arquivo de pedidos cresce durante a execução. Nenhum desses resultados representa SLA, capacidade de usuários ou carga distribuída. As 480 execuções não devem ser somadas aos 79 métodos de teste como se fossem uma única suíte.

## Verificação do pacote instalado

```bash
python -m pip wheel . --no-deps --wheel-dir dist
python scripts/verify_wheel.py dist/banco_agil-0.1.0-py3-none-any.whl
```

A construção pode baixar ferramentas de build. A verificação instala o wheel offline em diretório temporário, confirma a origem do módulo e executa login, consulta e encerramento fora do checkout. Isso verifica sementes empacotadas e independência da pasta original; não verifica instalação da UI ou compatibilidade de todas as plataformas.

## CI e critérios de entrega

O workflow tem disparo manual (`workflow_dispatch`); push e pull request não executam a CI. A configuração foi escolhida após o candidato informar o limite de uso do GitHub Actions atingido. Nenhuma aprovação remota é atribuída ao projeto; o relatório local é a evidência disponível.

O [workflow configurado](../.github/workflows/ci.yml) instala os extras, roda suíte e lint, microbenchmark, avaliação demo com gate, carga local reduzida e verificação do wheel. A execução remota ainda está pendente porque o projeto permanece local.

Para avaliar uma nova versão, registrar ambiente, data, quantidade de testes, skips e falhas; revisar os relatórios gerados e atualizar [VALIDATION.md](VALIDATION.md). Resultados de benchmark variam com ambiente e amostragem; a CI atual verifica execução, mas não impõe teto de latência. A avaliação demo exige acerto integral somente nos casos conhecidos.

## O que ainda não foi validado

- Qualidade, latência e custo de Gemini real em um holdout independente.
- Conversas livres longas, referências a mensagens anteriores e extração de múltiplos campos.
- Pentest, testes contra LLM real e auditoria de vulnerabilidades das dependências.
- Persistência de sessão, recuperação após crash e idempotência entre instâncias.
- Carga distribuída, testes de longa duração e disponibilidade prolongada de provedores.
- Inspeção visual no navegador, uso em diferentes tamanhos de tela e acessibilidade.
- Compatibilidade fora do ambiente local validado; a CI Linux/Python 3.11 está preparada, ainda sem execução remota registrada.

Os testes automatizados de UI usam AppTest; não equivalem a testes ponta a ponta com navegador real. Testes aprovados comprovam as condições exercitadas, não garantem segurança ou qualidade universais.
