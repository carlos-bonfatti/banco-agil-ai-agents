"""Políticas conservadoras para comandos e moedas, compartilhadas pelos adaptadores."""

import re

from banco_agil.domain import normalize


def positive_clauses(message: str) -> str:
    clauses = re.split(r"[,;.!?]|\b(?:mas|porem|so)\b", normalize(message))
    return " ".join(
        clause for clause in clauses if not re.search(r"\b(?:nao|nunca|nem)\b", clause)
    ).strip()


def wants_end(message: str) -> bool:
    value = positive_clauses(message)
    value = re.sub(r"^(?:obrigado|obrigada)\s+", "", value)
    if not value:
        return False
    # Encerrar uma tarefa não equivale a encerrar todo o atendimento.
    if re.search(r"\b(consulta|cotacao|tarefa|pedido|entrevista)\b", value):
        return False
    if value in {"sair", "fim", "encerrar", "finalizar", "terminar", "tchau", "parar"}:
        return True
    return bool(
        re.fullmatch(
            r"(?:(?:eu )?quero |pode |por favor )?"
            r"(?:encerrar|encerre|finalizar|finalize|terminar|termine|parar|cancelar|sair(?: de)?)"
            r"(?: (?:o |a |este |esta |meu |minha )?(?:atendimento|conversa))?(?: por favor)?",
            value,
        )
    )


def requested_currency(message: str) -> str | None:
    """USD é o padrão somente quando nenhuma moeda diferente é explicitamente pedida."""
    value = positive_clauses(message)
    if re.search(
        r"\b(cad|jpy|aud|chf|cny|ars|mxn|btc|inr|rub|krw|aed|zar|canadense|australiano|"
        r"iene|yen|franco|peso|yuan|bitcoin|rupia|rublo|won|dirham|rand)\b",
        value,
    ):
        return "UNSUPPORTED"
    # Recusa uma moeda desconhecida explicitamente nomeada após cotação/moeda.
    named = re.findall(r"\b(?:cotacao|moeda)\s+(?:d[aeo]\s+)?([a-z]{3,})\b", value)
    generic = {"por", "atual", "agora", "hoje", "compra", "venda", "simulada", "real", "tempo"}
    supported = {"usd", "eur", "gbp", "dolar", "euro", "libra"}
    if any(name not in generic | supported for name in named):
        return "UNSUPPORTED"
    currencies = set()
    for currency, pattern in {
        "USD": r"\b(dolar|usd)\b",
        "EUR": r"\b(euro|eur)\b",
        "GBP": r"\b(libra|gbp)\b",
    }.items():
        if re.search(pattern, value):
            currencies.add(currency)
    if len(currencies) > 1:
        return "MULTIPLE"
    return next(iter(currencies), None)
