# Revisão antes da publicação

Data: 05/10/2026. Revisão local, sem novas chamadas de LLM ou ativação de faturamento.

## Verificações realizadas

- 79 testes aprovados, sem skips; lint e formatação Ruff aprovados.
- `git diff --check` no trabalho e no índice sem problemas de whitespace.
- `pip check` sem conflitos de dependências. Isso não é auditoria de vulnerabilidades conhecidas.
- `.gitignore` verificado com `.env`, variantes locais, chaves privadas, `.ssh`, `.aws`, `.codex`, ambiente virtual, runtime, build e dist. `.env.example` está incluído com chave vazia.
- Arquivos candidatos à publicação examinados por padrões de chaves de API, tokens e chaves privadas. Não foram encontrados padrões de credenciais; essa busca não garante ausência de todo segredo possível.
- Cadastros incluídos são sementes fictícias do desafio. CSVs alterados pelo uso da interface permanecem em `runtime/`, excluído da publicação.
- CI configurada com `contents: read`, lint, formatação, testes, avaliação offline, benchmarks e instalação do wheel. Ainda não executada no GitHub.

## Correção encontrada na revisão

Data de nascimento compacta (DDMMAAAA) agora também é ocultada nas mensagens de menu e no payload do classificador. O teste simula HTTP e verifica ambos os efeitos. Antes da correção, o formato sem barras só era ocultado pelo tratamento específico da etapa de nascimento.

## Controles de segurança examinados

Identidade vem da sessão autenticada; ferramentas financeiras verificam autenticação e expiração. O LLM só retorna intenção e moeda, validadas por enum e estrutura. Valores, score e decisões vêm de código/CSV/API. Chave Gemini é enviada em header. Logs técnicos não incluem mensagem ou identificadores. As URLs externas são definidas pelos adaptadores; o cliente não fornece uma URL de consulta. Escritas CSV são atômicas e protegidas por lock local; pedidos têm idempotência. HTML customizado da interface é estático e não recebe entrada do cliente.

Autenticação CPF/nascimento é fictícia e não adequada para produção. Limites de chamadas e locks são locais. Sessões não persistem. A redação usa padrões e não identifica universalmente dados pessoais. Não foi realizada auditoria externa, pentest, análise completa de dependências por CVE, acessibilidade ou E2E de navegador.

## Aderência ao enunciado

| Exigência | Resultado e limites |
|---|---|
| Saudação, CPF/nascimento, cadastro e até três falhas | Implementado e testado; formatos com/sem separadores aceitos |
| Consulta de limite e pedido de aumento com colunas CSV | Implementado e testado; decisão registrada, sem efetivar limite |
| Aprovar/rejeitar por tabela de score | Implementado; tabela sintética, pois o enunciado não fornece valores numéricos |
| Entrevista de cinco perguntas, score e reanálise | Implementado e testado |
| Cotação por API externa | Adaptador real validado em 04/10; demonstração exige BANCO_FX_MODE=live; padrão é simulado |
| Encerrar a qualquer momento e tratar erros | Implementado e testado nos casos conhecidos |
| Tom, escopo e transições implícitas | Persona exclusiva do Banco Ágil; sessão/handlers controlam o fluxo |
| Agentes especializados | Quatro responsabilidades em handlers; Gemini classifica intenções. Não são quatro agentes LLM autônomos; explicar a escolha e reconhecer a interpretação arquitetural |
| UI para atendimento completo | AppTest de jornada passou; interface final aprovada pelo candidato; E2E de navegador não implementado |
| README com as seções solicitadas | Seções de visão geral, arquitetura, funcionalidades, desafios, escolhas e execução/testes presentes |
| Repositório público no GitHub | Remoto informado e Git inicializado; commit/push e CI remota ainda pendentes |

O smoke real do candidato registra cinco chamadas Gemini corretas e zero erros; outros 21 casos foram locais e 28 omitidos. Não apresentar como avaliação integral do modelo. RAG, fine-tuning, tracing centralizado e recuperação de conversas anteriores não são exigências explícitas do enunciado.

Parecer: a base funcional está revisada e pode seguir para publicação do desafio com limites explícitos. Não afirmar conformidade total enquanto publicação/CI estiverem pendentes. Não afirmar ausência universal de vulnerabilidades ou alucinações.
