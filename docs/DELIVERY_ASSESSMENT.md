# Avaliação de maturidade e apresentação

Avaliação baseada no código e nas verificações locais de 04/10/2026. Não é uma classificação profissional do candidato nem garantia de contratação. Sem descrição da vaga e critérios internos da empresa, os diferenciais abaixo são inferências sobre a relevância para o desafio bancário.

## Nível demonstrado

Protótipo de desafio com boas evidências de engenharia sênior e decisões compatíveis com raciocínio de especialista. Ainda não há evidência suficiente para qualificá-lo como sistema de agentes de nível especialista em produção. O uso de IA é restrito à classificação de intenções; as quatro responsabilidades são handlers determinísticos, não quatro agentes autônomos. Essa decisão reduz risco e custo, mas deve ser explicada ao avaliador sem exagerar a arquitetura.

## Diferenciais sustentados por evidências

| Diferencial | Evidência | Valor para o cenário do desafio |
|---|---|---|
| Autoridade financeira em código | Autenticação nas ferramentas, Decimal e tabela de score; modelo não escolhe o cliente nem aprova crédito | Evita que texto gerado tenha autoridade sobre decisões bancárias |
| Aderência ao escopo | Atendimento exclusivo do Banco Ágil; testes verificam ausência de chamadas e alterações indevidas | Restringe identidade, instituição e serviços disponíveis |
| Qualidade comportamental | 79 testes, regressões e jornada AppTest; 54 casos offline conhecidos | Torna alterações verificáveis e reproduzíveis |
| Integridade dos registros | Lock de arquivo, escrita atômica, idempotência e testes multiprocessos | Protege pedidos contra duplicação e perda nos cenários locais testados |
| FinOps proporcional | IA somente no menu, tetos de chamadas, uso reportado de tokens e cache de câmbio | Controla trabalho externo sem inventar custo quando faltam dados |
| Escalabilidade medida | 480 execuções locais com bases crescentes; serialização de CSV documentada | Fundamenta a migração de armazenamento com dados, sem prometer escala inexistente |
| Entrega reproduzível | Wheel instalado e executado fora do checkout; documentação e CI configurada | Reduz dependência da máquina do autor e facilita avaliação |

## Limites que devem acompanhar a apresentação

- Smoke Gemini real passou em cinco chamadas; avaliação completa e conjunto independente ainda pendentes. Os 54/54 offline não provam qualidade do modelo.
- Observabilidade local, sem tracing centralizado ou histórico persistente de conversa.
- Interface final aprovada visualmente pelo candidato em 05/10/2026; sem E2E de navegador ou verificação de acessibilidade.
- CSV e sessões em memória não oferecem operação distribuída; autenticação fictícia serve ao desafio.
- Repositório público e execução remota da CI ainda pendentes.

## Antes de entregar

1. Smoke real já registrado em VALIDATION.md. Avaliação completa permanece opcionalmente pendente sob a restrição atual de não realizar novas chamadas externas.
2. Demonstrar cotação com `BANCO_FX_MODE=live`; integração real e cache já foram verificados, mas o padrão é demo.
3. Interface final aprovada pelo candidato em 05/10/2026. Essa aprovação não substitui E2E nem auditoria de acessibilidade.
4. Publicar o repositório e verificar CI no ambiente remoto; a publicação exige definição de conta/repositório.

## Como apresentar

“Construí um atendimento bancário com contexto controlado por sessão. A IA interpreta intenções, enquanto identidade, valores e decisões são verificados em código. Testei comportamentos e efeitos proibidos, controlei chamadas externas e medi o limite do armazenamento CSV. O projeto é reproduzível, e as limitações de produção estão documentadas.”

O diferencial é conectar cada escolha a risco, custo, experiência do cliente e evidência. Acrescentar frameworks sem necessidade ou apresentar simulação como avaliação real enfraquece essa demonstração.
