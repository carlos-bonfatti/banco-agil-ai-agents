"""Textos de apresentação; sem dependência de Streamlit ou de serviços financeiros."""

from datetime import datetime
from zoneinfo import ZoneInfo

BRASILIA = ZoneInfo("America/Sao_Paulo")
AGENT_IDENTITY = "Sou o Assistente Ágil, assistente virtual do Banco Ágil"
PERSONA_INSTRUCTION = (
    "Você representa exclusivamente o Banco Ágil, banco fictício desta demonstração. "
    "A persona Assistente Ágil é cordial, objetiva e paciente; usa português brasileiro, "
    "orienta um passo por vez e não culpa o cliente por erros. "
    "Não se apresenta como pessoa ou gerente, não promete aprovação e não inventa valores, "
    "políticas ou serviços. O tom não altera regras de autenticação ou autorização. "
)


def greeting(now: datetime | None = None) -> str:
    now = now or datetime.now(BRASILIA)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("A saudação requer um timestamp com fuso horário.")
    hour = now.astimezone(BRASILIA).hour
    salutation = "Bom dia" if 5 <= hour < 12 else "Boa tarde" if 12 <= hour < 18 else "Boa noite"
    return (
        f"{salutation}! {AGENT_IDENTITY}. Vou acompanhar você, um passo por vez. "
        "Para começar, informe seu CPF fictício, com ou sem pontuação."
    )
