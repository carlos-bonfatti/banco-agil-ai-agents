"""Limites do atendimento; mencionar outra instituição não implica recusa automática."""

import re

from banco_agil.domain import normalize
from banco_agil.intent_policy import positive_clauses

HELP = "Posso consultar seu limite, solicitar aumento, atualizar seu score ou consultar câmbio."
SCOPE_NAMES = {"identity", "other_bank", "unsupported_service"}
BANKS = r"(?:itau|nubank|bradesco|santander|inter|caixa|banco do brasil|banco teste)"


def scope_intent(message: str) -> str | None:
    """Reconhece casos explícitos; o modelo continua responsável pelas demais intenções."""
    value = positive_clauses(message)
    if re.search(
        rf"\b(?:voce|voces|vc)\s+(?:e|sao|representa|representam)\s+(?:o |a )?(?:banco\b|{BANKS}\b)"
        r"|\bquem e voce\b|\bqual (?:banco|instituicao) (?:voce|voces|vc|representa|atende)\b"
        rf"|\b(?:finja ser|aja como|represente)\s+(?:o |a )?{BANKS}\b",
        value,
    ):
        return "identity"
    if re.search(
        r"\breceita (?:de|para)\b|\b(?:me de|quero|ensine|mostre|mande) (?:uma )?receita\b"
        r"|\b(?:conte|contar) (?:uma )?piada\b",
        value,
    ):
        return "unknown"
    # Serviços bancários legítimos, mas não implementados neste atendimento.
    for clause in re.split(r"[,;.!?]|\b(?:mas|porem|so)\b", normalize(message)):
        clause = positive_clauses(clause)
        # Uma finalidade ou evento passado não equivale a pedir esse serviço.
        if re.search(r"\b(?:limite|score|cotacao|cambio)\b", clause):
            clause = re.split(r"\b(?:para|porque|pois|depois|apos)\b", clause)[0]
        service = re.search(
            r"\b(?:transferencias?|pix|ted|saldo|extrato|emprestimos?|investimentos?)\b", clause
        )
        request = re.search(
            r"\b(?:como|posso|pode|quero|preciso|gostaria|permitem|permite|oferecem|oferece|"
            r"consultar|consulta|ver|mostrar|qual|quanto|fazer|realizar|enviar)\b",
            clause,
        )
        direct = re.search(
            r"\b(?:transferir|transfira|investir|envie pix|faca pix)\b"
            r"|\b(?:abrir|abro|abertura de) (?:uma |minha |a )?conta\b"
            r"|\b(?:pagar|pagamento de) (?:um |uma |minha |meu |a |o )?(?:fatura|boleto)\b"
            r"|\bsolicitar (?:um |novo |o )?cartao\b",
            clause,
        )
        if (
            direct
            or (service and request)
            or clause
            in {
                "saldo",
                "extrato",
                "pix",
                "transferencia",
                "transferencias",
                "emprestimo",
                "investimentos",
            }
        ):
            return "unsupported_service"
    # A instituição precisa qualificar o dado pedido, não apenas aparecer na mensagem.
    foreign = rf"(?:(?:banco )?{BANKS}|banco (?!agil\b|de dados\b)[a-z]+)"
    qualified = (
        r"\b(?:limite|score|credito|cotacao)\s+"
        r"(?:(?:de credito|disponivel|atual|total|meu)\s+)*"
        rf"(?:(?:no|na|do|da)\s+)?(?:cartao (?:do |da )?)?{foreign}\b"
    )
    for clause in re.split(r"[,;.!?]|\b(?:mas|porem|so)\b", normalize(message)):
        secondary = re.search(rf"\b(?:e|tambem) (?:no|na|do|da) {foreign}\b", clause)
        financial = re.search(r"\b(?:limite|score|credito|cotacao)\b", clause)
        if not re.search(r"\b(?:nao|nunca|nem)\b", clause) and (
            re.search(qualified, clause) or (financial and secondary)
        ):
            return "other_bank"
    if re.search(rf"^(?:no|na|do|da) {foreign}\b.*\b(?:limite|score|credito|cotacao)\b", value):
        return "other_bank"
    return None


def scope_response(name: str) -> str:
    if name == "identity":
        return (
            "Sou o Assistente Ágil, assistente virtual do Banco Ágil, "
            "o banco fictício desta demonstração. Vou orientar você, um passo por vez. " + HELP
        )
    if name == "other_bank":
        return (
            "Atendo pelo Banco Ágil e não tenho acesso a dados ou políticas de outros bancos. "
            + HELP
        )
    if name == "unsupported_service":
        return "Essa funcionalidade não está disponível neste atendimento do Banco Ágil. " + HELP
    return (
        "Sou o assistente do Banco Ágil. Esse pedido está fora do escopo deste atendimento. " + HELP
    )
