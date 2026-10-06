import logging
import math
import re
import time
from datetime import datetime
from threading import Lock
from uuid import uuid4

from banco_agil.domain import (
    DomainError,
    InfrastructureError,
    Interview,
    birth_value,
    cpf_value,
    money,
    normalize,
)
from banco_agil.intent_policy import requested_currency, wants_end
from banco_agil.ports import ExchangeProvider, IntentInterpreter
from banco_agil.scope_policy import HELP, SCOPE_NAMES, scope_intent, scope_response
from banco_agil.service import BankingService
from banco_agil.session import Session

logger = logging.getLogger("banco_agil")
GREETING = "Olá! Sou o assistente do Banco Ágil. Para começar, informe seu CPF."
MENU = HELP
QUESTIONS = {
    "income": "Qual é sua renda mensal?",
    "employment": "Seu emprego é formal, autônomo ou está desempregado?",
    "expenses": "Qual é o total das suas despesas fixas mensais?",
    "dependents": "Quantos dependentes você possui?",
    "debts": "Você possui dívidas ativas? Responda sim ou não.",
}


def brl(value):
    return "R$ " + f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


class Engine:
    def __init__(
        self,
        service: BankingService,
        interpreter: IntentInterpreter,
        exchange: ExchangeProvider,
        *,
        max_session_calls: int = 20,
        max_engine_calls: int = 200,
        session_timeout: float = 900,
    ):
        if (
            max_session_calls < 1
            or max_engine_calls < 1
            or not math.isfinite(session_timeout)
            or session_timeout <= 0
        ):
            raise ValueError("Limites de chamadas e duração da sessão devem ser positivos.")
        self.service = service
        self.interpreter = interpreter
        self.exchange = exchange
        self.max_session_calls = max_session_calls
        self.max_engine_calls = max_engine_calls
        self.session_timeout = session_timeout
        self.metrics_lock = Lock()
        self.metrics = {
            "turns": 0,
            "llm_calls": 0,
            "llm_input_tokens": 0,
            "llm_output_tokens": 0,
            "llm_failures_without_usage": 0,
            "llm_responses_without_usage": 0,
            "dependency_errors": 0,
        }

    def metrics_snapshot(self) -> dict[str, int]:
        with self.metrics_lock:
            return dict(self.metrics)

    def _count(self, name: str, count: int = 1) -> None:
        with self.metrics_lock:
            self.metrics[name] += count

    def _interpret(self, session: Session, message: str):
        external = getattr(self.interpreter, "external", False)
        if external:
            with self.metrics_lock:
                if session.llm_calls >= self.max_session_calls:
                    raise DomainError(
                        "O limite de consultas à IA desta sessão foi atingido. "
                        "Encerre o atendimento ou cancele a tarefa atual."
                    )
                if self.metrics["llm_calls"] >= self.max_engine_calls:
                    raise DomainError("O limite de consultas à IA deste ambiente foi atingido.")
                session.llm_calls += 1
                self.metrics["llm_calls"] += 1
        try:
            intent = self.interpreter.interpret(message)
        except InfrastructureError:
            if external:
                self._count("llm_failures_without_usage")
            raise
        self._count("llm_input_tokens", intent.input_tokens)
        self._count("llm_output_tokens", intent.output_tokens)
        if external and not intent.usage_known:
            self._count("llm_responses_without_usage")
        return intent

    def respond(self, session: Session, message: str, event_id: str | None = None) -> str:
        event_id = event_id or str(uuid4())
        if not message.strip() or len(message) > 2000 or len(event_id) > 80:
            return "Envie uma mensagem de 1 a 2.000 caracteres."
        start = time.perf_counter()
        with session.lock:
            if session.stage == "closed":
                return "Este atendimento foi encerrado. Inicie uma nova conversa."
            if session.cpf is not None:
                try:
                    session.authenticated_cpf()
                except DomainError as exc:
                    return str(exc)
                session.last_activity = time.monotonic()
            cached = session.responses.get(event_id)
            if cached:
                if cached[0] != message:
                    return "Identificador de mensagem já utilizado com outro conteúdo."
                return cached[1]
            try:
                response = self._dispatch(session, message, event_id)
            except DomainError as exc:
                response = str(exc)
            except (InfrastructureError, OSError, KeyError, ValueError) as exc:
                # Não registrar mensagem, CPF, dados financeiros ou exceção com payload.
                logger.warning("dependency_failure type=%s", type(exc).__name__)
                self._count("dependency_errors")
                response = "Não consegui concluir agora. Seus dados de entrada foram preservados; tente novamente."
                if session.stage in QUESTIONS:
                    response += " " + QUESTIONS[session.stage]
                # Falhas transitórias não entram no cache de idempotência.
                return response
            if session.stage != "closed":
                if len(session.responses) >= 128:
                    session.responses.pop(next(iter(session.responses)))
                session.responses[event_id] = (message, response)
            self._count("turns")
            logger.info(
                "turn stage=%s latency_ms=%.2f", session.stage, (time.perf_counter() - start) * 1000
            )
            return response

    def _dispatch(self, s: Session, message: str, event: str) -> str:
        if wants_end(message):
            s.close()
            return "Atendimento encerrado. Obrigado por falar com o Banco Ágil!"
        if s.stage in {"cpf", "birth"}:
            return self.triage(s, message)
        s.authenticated_cpf()
        if normalize(message).strip(".!? ") in {"cancelar", "cancelar tarefa", "voltar ao menu"}:
            s.stage = "menu"
            s.interview.clear()
            s.desired_limit = None
            return "Etapa atual cancelada. Pedidos já registrados foram preservados. " + MENU
        if s.stage in QUESTIONS:
            return self.interview(s, message, event)
        if s.stage == "offer_interview":
            value = normalize(message).strip(".! ")
            if value in {"sim", "quero", "aceito"}:
                s.stage = "income"
                return QUESTIONS[s.stage]
            if value in {"nao", "agora nao"}:
                s.stage = "menu"
                s.desired_limit = None
                return MENU
            return "Deseja realizar a entrevista para atualizar seu score? Responda sim ou não."
        if s.stage == "amount":
            return self.credit(s, "increase", message, event)
        scope = scope_intent(message)
        if scope is not None:
            return scope_response(scope)
        intent = self._interpret(s, message)
        if intent.name in SCOPE_NAMES or intent.name == "unknown":
            return scope_response(intent.name)
        if intent.name == "ambiguous":
            return "Vamos resolver uma solicitação por vez. " + MENU
        if intent.name == "interview":
            s.stage = "income"
            return QUESTIONS[s.stage]
        if intent.name in {"limit", "increase"}:
            return self.credit(s, intent.name, message, event)
        if intent.name == "exchange":
            currency = requested_currency(message) or intent.currency
            return self.currency(s, currency)
        return MENU

    def triage(self, s: Session, message: str) -> str:
        if s.stage == "cpf":
            s.pending_cpf = cpf_value(message)
            s.stage = "birth"
            return "Informe sua data de nascimento (DD/MM/AAAA ou DDMMAAAA)."
        birth = birth_value(message)
        client = self.service.repository.authenticate(s.pending_cpf or "", birth)
        if client is None:
            s.failures += 1
            s.pending_cpf = None
            if s.failures >= 3:
                s.close()
                return "Não foi possível autenticar após três tentativas. Atendimento encerrado."
            s.stage = "cpf"
            return (
                f"Não consegui autenticar. Restam {3 - s.failures} tentativa(s). Informe seu CPF."
            )
        s.cpf = client.cpf
        s.last_activity = time.monotonic()
        s.idle_timeout_seconds = self.session_timeout
        s.pending_cpf = None
        s.stage = "menu"
        return "Autenticação concluída. " + MENU

    def credit(self, s: Session, intent: str, message: str, event: str) -> str:
        if intent == "limit":
            return "Seu limite disponível é " + brl(self.service.limit(s)) + "."
        if s.stage != "amount":
            s.stage = "amount"
            return "Qual é o novo limite total desejado? Informe somente o valor."
        amount = money(message)
        result = self.service.request(s, amount, event)
        if result.status == "aprovado":
            s.stage = "menu"
            s.desired_limit = None
            return (
                f"Solicitação de {brl(amount)} aprovada pela regra de score. "
                "A decisão foi registrada; a efetivação do limite não faz parte desta simulação."
            )
        s.stage = "offer_interview"
        s.desired_limit = amount
        return "Solicitação rejeitada pelo score atual. Deseja uma entrevista para atualizar seu score?"

    def interview(self, s: Session, message: str, event: str) -> str:
        stage = s.stage
        value = normalize(message).strip(".! ")
        if stage in {"income", "expenses"}:
            answer = money(message)
        elif stage == "employment":
            aliases = {
                "formal": "formal",
                "autonomo": "autonomo",
                "desempregado": "desempregado",
                "desempregada": "desempregado",
            }
            if value not in aliases:
                raise DomainError(QUESTIONS[stage])
            answer = aliases[value]
        elif stage == "dependents":
            if not re.fullmatch(r"[0-9]{1,2}", value):
                raise DomainError("Informe um número de dependentes entre 0 e 99.")
            answer = int(value)
        else:
            if value not in {"sim", "nao"}:
                raise DomainError(QUESTIONS[stage])
            answer = value == "sim"
        s.interview[stage] = answer
        stages = list(QUESTIONS)
        if stage != "debts":
            s.stage = stages[stages.index(stage) + 1]
            return QUESTIONS[s.stage]
        score = self.service.interview(s, Interview(**s.interview))
        # Uma nova análise usa uma nova identidade; reenvios do mesmo turno são deduplicados.
        if s.desired_limit is not None:
            amount = s.desired_limit
            result = self.service.request(s, amount, event + ":review")
            s.stage = "menu"
            s.interview.clear()
            s.desired_limit = None
            return (
                f"Score atualizado para {score}. Nova análise de {brl(amount)}: {result.status}. "
                "Decisão registrada. " + MENU
            )
        s.stage = "menu"
        s.interview.clear()
        return f"Score atualizado para {score}. " + MENU

    def currency(self, s: Session, currency: str) -> str:
        s.authenticated_cpf()
        if currency == "MULTIPLE":
            return "Qual moeda deseja consultar primeiro: USD, EUR ou GBP?"
        if currency == "UNSUPPORTED":
            return "Moeda não suportada. Posso consultar USD, EUR ou GBP. Qual deseja?"
        quote = self.exchange.quote(currency)
        label = "COTAÇÃO SIMULADA" if quote.simulated else "Cotação de compra (bid)"
        stamp = datetime.fromisoformat(quote.observed_at).strftime("%d/%m/%Y %H:%M UTC")
        return (
            f"{label}: 1 {quote.currency} = {brl(quote.rate)}. "
            f"Fonte: {quote.source}; referência: {stamp}. Consulta concluída."
        )
