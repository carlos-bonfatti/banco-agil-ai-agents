# Validação da implementação revisada

Suíte, lint, formatação e avaliação offline reexecutados em 05/10/2026, macOS, Python 3.12. Medições de carga, build e API de câmbio abaixo são de 04/10/2026, conforme indicado; não foram repetidas na conclusão sem novas chamadas externas.

Este documento registra resultados de execução. Classificação, procedimentos e limites dos testes estão em [TESTING.md](TESTING.md); controles e riscos estão em [SECURITY_AND_CONTEXT.md](SECURITY_AND_CONTEXT.md). Atualizar a documentação não representa uma nova execução das verificações.

## Núcleo

79 testes executados e aprovados, sem skips, incluindo jornada completa na UI Streamlit, casos de escopo na interface e integração LangGraph. Ruff e verificação de formatação passaram. Teste de concorrência usa quatro processos e dezesseis pedidos distintos; todos os registros são preservados.

Casos cobrem autenticação, três falhas, limite, dinheiro, score, reanálise, isolamento, idempotência, encerramento com negação, cancelamento de tarefa, expiração antes de acesso ao serviço/cache, limites de chamadas entre sessões concorrentes, redação, validação de CSV, falhas de dependência, escrita atômica e saída estruturada Gemini. A jornada de UI inclui rejeição, entrevista, aprovação na reanálise, câmbio, cancelamento e encerramento. Testes do adaptador usam respostas HTTP simuladas, não uma chave real.

## Microbenchmark

Medição repetida na validação final local de 04/10/2026.

300 consultas de limite já autenticadas em processo único e CSV temporário pequeno:

- p50: 0,098 ms.
- p95: 0,125 ms.
- Chamadas externas e tokens: zero, por ser modo demo.

Esses números são microbenchmark do núcleo local e não estimativa de latência do aplicativo, LLM, rede ou produção. Reexecutar `python scripts/benchmark.py` para medir no computador do avaliador.

## Avaliação de roteamento offline

54/54 casos de regressão aprovados, sem erro ou caso omitido. O relatório [evaluation-demo.json](evaluation-demo.json) registra resultados por categoria, matriz de confusão, custos e escopo. Latência observada: p50 0,035 ms; p95 0,085 ms; p99 0,205 ms. Chamadas externas: zero; custo do modelo: zero. Isso não representa custo total da aplicação nem avalia um LLM real.

## Smoke test Gemini real

Executado pelo candidato em seu terminal em 05/10/2026 e conferido no relatório [evaluation-gemini-smoke.json](evaluation-gemini-smoke.json). Modelo `gemini-3.5-flash-lite`: cinco chamadas externas, cinco classificações corretas, zero erros do provedor. Outros 21 casos foram resolvidos por políticas locais; 28 foram omitidos pelo limite. Portanto, 26/26 casos executados passaram, mas não houve avaliação completa de 54 casos nem holdout independente.

Consumo reportado nessa avaliação: 1.879 tokens de entrada e 88 de saída incluindo pensamento, sem chamadas de uso desconhecido. O custo estimado permanece nulo porque as tarifas não foram informadas. O candidato mostrou o projeto no nível gratuito no AI Studio; esse relatório não consulta faturamento e não representa fatura. Nenhuma nova chamada Gemini foi executada pelo agente na conclusão sem custos adicionais. A latência do relatório mistura políticas locais e chamadas remotas.

Os casos foram usados no desenvolvimento das correções. Não constituem holdout independente. O runner avalia interpretação junto com políticas locais de encerramento e moeda. A CI configurada exige acerto integral desses casos conhecidos para impedir regressão.

## Carga local com crescimento da base

Medição repetida na validação final local de 04/10/2026.

12 cenários com 40 amostras cada: 480 execuções bem-sucedidas, sem chamadas externas. Bases sintéticas com 2, 1.000 e 10.000 clientes e igual quantidade inicial de pedidos; um processo com 1 ou 4 threads.

| Clientes / pedidos iniciais | Threads | p95 login + limite (ms) | p95 análise/gravação de aumento (ms) |
|---|---|---|---|
| 2 | 1 | 0,350 | 0,730 |
| 2 | 4 | 1,733 | 1,939 |
| 1.000 | 1 | 2,316 | 3,588 |
| 1.000 | 4 | 9,245 | 12,142 |
| 10.000 | 1 | 19,709 | 28,636 |
| 10.000 | 4 | 81,333 | 114,274 |

Detalhes em [performance-demo.json](performance-demo.json). A latência de análise/gravação exclui login; o throughput inclui a preparação e a execução completa de cada cenário. Os pedidos crescem durante a medição. Com 10.000 registros, a taxa dos cenários de aumento ficou em 26,95 execuções/s com uma thread e 26,62 com quatro. Esse comportamento evidencia serialização e leitura/reescrita do CSV; aumentar concorrência não resolve o gargalo.

Não interpretar esses valores como capacidade de usuários, SLA ou teste distribuído. p99 com 40 amostras se aproxima do máximo observado. Repetir com mais amostras para planejamento de produção. Os dados reais de trabalho não foram alterados pelo benchmark.

## Empacotamento e controles de consumo

A geração e instalação do wheel foram repetidas na validação final. O build sem isolamento falhou por ausência de setuptools no ambiente; o build isolado baixou a dependência temporária e concluiu. `pip check` também passou.

Wheel gerado e instalado offline em diretório temporário. O teste verificou que o módulo carregado veio da instalação, e não do checkout, e executou autenticação, consulta de limite e encerramento usando sementes empacotadas. Comando reproduzível: `python scripts/verify_wheel.py caminho/do/pacote.whl`.

Testes verificam teto compartilhado por Engine sob concorrência, consumo de tentativa em falha, continuidade de encerramento após o teto e custo incompleto quando o provedor não informa uso. A rodada de 04/10 não executou Gemini real; o smoke posterior do candidato está registrado acima. A cotação externa foi validada conforme registro abaixo. A estimativa monetária depende de tarifas explicitamente fornecidas e não é um teto de faturamento.

## Correção de aderência ao escopo

Foram acrescentados oito testes, com subcasos de identidade, receitas, instruções adversariais, serviços não implementados, referências a outras instituições e recusas indevidas. Casos recusados verificam ausência de leitura financeira, escrita de pedidos, atualização de score, cotação e chamada ao interpretador, além de CSVs inalterados.

O bug de “meu limite no Itaú” foi corrigido: não apresenta mais o limite do Banco Ágil nessa resposta. A abertura de conta/transferência/pagamento é informada como indisponível neste atendimento, sem inventar políticas bancárias. Salário/PIX de outro banco e boleto como motivo da consulta não bloqueiam a consulta legítima.

Também passaram testes de escopo pela interface AppTest e de novas intenções Gemini via HTTP simulado. Isso não é avaliação de Gemini real nem E2E de navegador. Nenhuma funcionalidade bancária fora do desafio foi implementada.

## Pendências de avaliação externa

- Qualidade de classificação com modelo real e conjunto de conversas de avaliação.
- Tokens faturáveis e custo por cenário com tarifas do provedor.
- Limites e disponibilidade prolongada da API de cotação (uma consulta real foi validada).
- Teste de carga distribuído após migração para armazenamento e sessões persistentes.
- Holdout independente para qualidade de roteamento e moedas.
- E2E de navegador e acessibilidade não executados. O candidato aprovou visualmente a interface final, conforme aceite registrado abaixo.
- CI remota: workflow preparado para execução manual (`workflow_dispatch`), sem execução aprovada registrada. O candidato informou limite de uso do GitHub Actions atingido; não foram feitas novas tentativas remotas. Publicação permanece uma etapa separada.

## Integrações verificadas

Streamlit 1.65.0 e LangGraph 1.2.12 instalados e testados. Nova consulta real à AwesomeAPI em 04/10/2026 retornou USD/BRL 5,2172, com referência do provedor em 02/10/2026 21:18:32 UTC. Segunda consulta no mesmo adaptador retornou o cache: uma chamada externa, um cache hit e zero erros. O timestamp do provedor está dentro da tolerância de três dias do adaptador; não representa atualização em tempo real nem preço de negociação. O modo padrão da aplicação permanece simulado.

Na autenticação, CPF com/sem pontuação e nascimento com/sem barras foram testados. Datas inexistentes/futuras e nascimento divergente do cadastro continuam recusados. A suíte atual totaliza 79 testes. Revisão visual foi tentada novamente, mas o serviço de controle nativo falhou ao iniciar e não disponibilizou navegador; não há validação visual automatizada nesta rodada.

## Aceite visual

Em 05/10/2026 o candidato aprovou a interface final. Esse é um aceite visual manual informado pelo usuário, não uma execução de E2E de navegador ou teste de acessibilidade. As tentativas automatizadas anteriores descritas acima permanecem como registro histórico.

## Pacote final

Em 05/10/2026 o wheel da versão final foi gerado e instalado offline em diretório temporário fora do checkout. A CLI instalada executou saudação por horário, autenticação, limite e encerramento. Nenhuma chamada LLM ou de câmbio foi feita nessa verificação.
