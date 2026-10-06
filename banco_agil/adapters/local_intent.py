import re

from banco_agil.domain import Intent
from banco_agil.intent_policy import positive_clauses, requested_currency
from banco_agil.scope_policy import scope_intent


class LocalInterpreter:
    """Modo de demonstração determinístico; não é um modelo de IA."""

    def interpret(self, message: str) -> Intent:
        scope = scope_intent(message)
        if scope is not None:
            return Intent(scope)
        value = positive_clauses(message)
        exchange = bool(re.search(r"\b(cambio|cotacao|dolar|euro|usd|eur|gbp|libra)\b", value))
        increase = bool(re.search(r"\b(aumentar|aumento|solicitar)\b", value))
        interview = value == "score" or bool(
            re.search(
                r"\bentrevista\b|\b(?:atualizar|recalcular|melhorar|reajustar)\s+(?:meu\s+)?score\b",
                value,
            )
        )
        limit_query = bool(
            re.search(r"\b(?:consultar|ver|mostrar)\s+(?:o\s+)?(?:meu\s+)?limite\b", value)
        )
        if sum((exchange, increase, interview)) > 1 or (
            limit_query and any((exchange, increase, interview))
        ):
            return Intent("ambiguous")
        if exchange:
            return Intent("exchange", requested_currency(message) or "USD")
        if increase:
            return Intent("increase")
        if interview:
            return Intent("interview")
        if re.search(r"\b(limite|credito)\b", value):
            return Intent("limit")
        return Intent("unknown")
