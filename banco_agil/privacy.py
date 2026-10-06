"""Redação defensiva de padrões conhecidos; não é um detector universal de dados pessoais."""

import re


def redact_sensitive(text: str) -> str:
    text = re.sub(
        r"(?<!\w)\d{3}[.\s]?\d{3}[.\s]?\d{3}[-\s]?\d{2}(?!\w)",
        "[CPF removido]",
        text,
    )
    text = re.sub(r"\b(?:\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})\b", "[data removida]", text)
    # O fluxo também aceita DDMMAAAA; proteger esse formato quando enviado no menu.
    text = re.sub(r"\b(?:0[1-9]|[12]\d|3[01])(?:0[1-9]|1[0-2])\d{4}\b", "[data removida]", text)
    text = re.sub(r"\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b", "[email removido]", text)
    text = re.sub(r"R\$\s*[\d.,]+", "[valor removido]", text, flags=re.I)
    return re.sub(
        r"\b(renda|sal[aá]rio|despesas|d[ií]vida)\s*(?:mensal\s*)?(?:[=:]|de)?\s*\d[\d.,]*",
        r"\1 [valor removido]",
        text,
        flags=re.I,
    )


def display_message(text: str, stage: str) -> str:
    if stage == "cpf":
        return "[CPF informado]"
    if stage == "birth":
        return "[Data de nascimento informada]"
    if stage in {"income", "expenses"}:
        return "[Valor financeiro informado]"
    return redact_sensitive(text)
