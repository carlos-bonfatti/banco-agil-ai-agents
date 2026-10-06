# Avaliação e roteiro de apresentação

## Evidências para defender a solução

A solução mantém identidade, cálculos, decisão e persistência em código; a IA interpreta a intenção no menu. Isso limita o alcance de uma resposta incorreta do modelo e reduz chamadas. Os quatro escopos são implementados no Engine, com contratos de infraestrutura separados. LangGraph é opcional e não oferece recuperação durável na implementação atual.

Apresentar os resultados junto com seu escopo: testes de integração simulados verificam robustez; casos offline verificam regressões; apenas uma execução com provedor real pode medir qualidade, disponibilidade, consumo e latência desse provedor.

## Avaliação offline de roteamento

```bash
python scripts/evaluate.py --mode demo
```

Dataset: `evaluation/intents.json`, 54 exemplos sintéticos com consultas, contexto de renda/score, negação, moedas suportadas e desconhecidas, pedidos conflitantes, encerramento, instruções adversariais, identidade institucional, serviços indisponíveis e referências legítimas a outros bancos. Resultado salvo em `docs/evaluation-demo.json`.

O relatório inclui acerto exato de intenção e moeda, erros, casos não executados por limite, matriz de confusão, resultados por categoria, latência p50/p95/p99 e chamadas externas. Comandos de encerramento/cancelamento e casos explícitos de escopo passam pela política local sem chamadas ao modelo. A moeda explicitamente reconhecida também é verificada em código. Portanto, o relatório avalia o conjunto adaptador + políticas, não o LLM isoladamente.

A CI configurada usa `--min-exact-match 1` para impedir regressões nos casos conhecidos do modo demo. O parâmetro é opcional, grava o relatório antes de falhar e não representa uma meta de qualidade de IA em produção.

Esse conjunto foi usado para corrigir defeitos conhecidos. Não é uma avaliação independente. Antes de comparar modelos, criar um holdout separado, congelar a versão dos datasets e registrar configuração do modelo. Evitar ajustar regras com base no holdout. Os casos adversariais do arquivo avaliam roteamento; proteção contra crédito indevido e acesso a outro cliente é verificada nos testes do serviço, não pelo acerto de classificação.

## Avaliação com Gemini, preparada mas não executada nesta rodada

Exige chave e modelo configurados. O modo precisa ser escolhido explicitamente:

```bash
python scripts/evaluate.py --mode gemini --max-calls 40
```

Esse comando usa a API externa e pode gerar custo. O limite é reservado antes de cada chamada; falhas consomem tentativa. Casos restantes ficam identificados como não executados. Comandos locais continuam sendo avaliados após o teto. Não há chamadas de câmbio nem operações bancárias no runner.

Para estimar custo, fornecer `--input-usd-per-million`, `--output-usd-per-million`, `--pricing-date` e `--pricing-source`. Não há tarifas presumidas. A estimativa usa tokens reportados, incluindo pensamentos quando informados, e fica marcada como incompleta se houver falha ou uso desconhecido. Não substitui a fatura e não inclui infraestrutura nem categorias especiais de cobrança. O limite de chamadas não é um teto garantido de valor faturado.

Comparar sempre custo e qualidade no mesmo dataset, com o mesmo escopo e limite. Reportar chamadas, modelo, data, tarifas, falhas e versão do código. Uma taxa de acerto em demo não estima qualidade Gemini.

## Performance com crescimento de CSV e concorrência

```bash
python scripts/benchmark.py
python scripts/benchmark_load.py
```

O primeiro comando mantém o microbenchmark de consulta autenticada. O segundo gera dados sintéticos em diretórios temporários, com 2, 1.000 e 10.000 clientes e igual quantidade inicial de pedidos, 40 amostras e 1/4 threads. Não altera `runtime/data/`.

Cenários:

- `login_and_limit`: inclui CPF, autenticação e leitura do limite, usando o último cliente do arquivo.
- `credit_write`: mede análise/persistência de aumento depois do login; throughput inclui preparação e execução completa do cenário. O arquivo cresce com os novos pedidos durante a medição.

Saída: `docs/performance-demo.json`, com ambiente, quantidade de dados, sucessos, latências e taxa de execução. O relatório usa um processo e threads; o teste de concorrência da suíte usa processos. Nenhum dos dois é teste distribuído. Com 40 amostras, p99 fica próximo do máximo observado; aumentar amostras e repetir medições antes de definir um SLA.

O crescimento da latência com volume e contenção sustenta a escolha de migrar o repositório, quando necessário. Evitar converter esses valores em capacidade de usuários ou latência de produção: não incluem UI, LLM, rede nem autenticação forte.

## Instalação reproduzível do pacote

```bash
python -m pip wheel . --no-deps --wheel-dir dist
python scripts/verify_wheel.py dist/banco_agil-0.1.0-py3-none-any.whl
```

O primeiro comando pode baixar ferramentas de build. O segundo é offline: instala o wheel sem dependências em uma pasta temporária, verifica que o módulo veio dessa instalação e executa autenticação, consulta e encerramento fora do checkout. Isso detecta ausência das sementes ou dependência indevida da pasta original.

## Demonstração de cinco minutos

1. Explicar a separação entre interpretação por IA e autoridade financeira em código.
2. Autenticar o cliente fictício, consultar limite e pedir R$ 10.000,00. Mostrar a rejeição pela regra vigente.
3. Aceitar entrevista: renda 20.000,00; emprego formal; despesas 1.000,00; zero dependentes; sem dívidas. Mostrar score 1000 e reanálise aprovada, com dois registros nos CSVs. A aprovação não efetiva o limite nesta simulação.
4. Consultar CAD e mostrar esclarecimento sem trocar por USD. Consultar EUR e mostrar fonte, horário e aviso de simulação; usar o modo live somente quando a integração tiver sido validada para a apresentação.
5. Demonstrar uma falha controlada ou apresentar seu teste, incluindo ausência de valor inventado.
6. Mostrar cancelamento de tarefa, encerramento e limpeza do histórico.
7. Apresentar as evidências de segurança, orçamento de chamadas, custo desconhecido em falhas e crescimento da latência com CSV. Explicar a próxima etapa de persistência transacional e sessões compartilhadas.

Antes da demonstração, usar uma cópia de dados nova. Não apagar a base de trabalho de um atendimento ativo. Não mostrar chaves, dados pessoais reais ou logs de mensagens. O repositório público exigido pelo desafio permanece uma etapa de entrega a ser realizada separadamente.
