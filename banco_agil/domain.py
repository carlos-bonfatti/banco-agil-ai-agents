import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


class DomainError(ValueError):
    """Entrada inválida ou operação não permitida."""


class InfrastructureError(RuntimeError):
    """Falha externa sem exposição de conteúdo sensível."""


def normalize(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn"
    ).strip()


def cpf_value(value: str) -> str:
    cleaned = re.sub(r"[.\-\s]", "", value)
    if not cleaned.isdigit() or len(cleaned) != 11:
        raise DomainError("Informe um CPF com 11 dígitos.")
    # Identificadores sintéticos são aceitos no ambiente do desafio.
    return cleaned


def birth_value(value: str) -> date:
    value = value.strip()
    if re.fullmatch(r"[0-9]{8}", value):
        value = f"{value[:2]}/{value[2:4]}/{value[4:]}"
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            result = datetime.strptime(value, fmt).date()
        except ValueError:
            continue
        if result > date.today():
            raise DomainError("A data não pode estar no futuro.")
        return result
    raise DomainError("Informe uma data válida: DD/MM/AAAA ou DDMMAAAA.")


def money(value: str) -> Decimal:
    cleaned = value.strip().replace("R$", "").replace(" ", "")
    if not re.fullmatch(r"[0-9]+(?:[.,][0-9]+)*", cleaned):
        raise DomainError("Informe um valor positivo, como 2500 ou 2.500,00.")
    if "," in cleaned:
        if not re.fullmatch(r"(?:[0-9]+|[0-9]{1,3}(?:\.[0-9]{3})+),[0-9]{1,2}", cleaned):
            raise DomainError("Valor monetário inválido.")
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif cleaned.count(".") > 1:
        if not re.fullmatch(r"[0-9]{1,3}(?:\.[0-9]{3})+", cleaned):
            raise DomainError("Valor monetário inválido.")
        cleaned = cleaned.replace(".", "")
    elif "." in cleaned and len(cleaned.rsplit(".", 1)[1]) == 3:
        cleaned = cleaned.replace(".", "")
    try:
        result = Decimal(cleaned)
        if not result.is_finite() or result < 0 or result > Decimal("1000000000"):
            raise DomainError("Valor fora do intervalo permitido.")
        if result.as_tuple().exponent < -2:
            raise DomainError("Use no máximo duas casas decimais.")
        return result.quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise DomainError("Valor monetário inválido.") from exc


@dataclass(frozen=True)
class Client:
    cpf: str
    name: str
    birth: date
    limit: Decimal
    score: int


@dataclass(frozen=True)
class Interview:
    income: Decimal
    employment: str
    expenses: Decimal
    dependents: int
    debts: bool

    def score(self) -> int:
        if self.employment not in {"formal", "autonomo", "desempregado"}:
            raise DomainError("Tipo de emprego inválido.")
        if (
            not self.income.is_finite()
            or not self.expenses.is_finite()
            or self.income < 0
            or self.expenses < 0
            or self.dependents < 0
        ):
            raise DomainError("Dados financeiros inválidos.")
        value = (self.income / (self.expenses + 1)) * 30
        value += {"formal": 300, "autonomo": 200, "desempregado": 0}[self.employment]
        value += {0: 100, 1: 80, 2: 60}.get(self.dependents, 30)
        value += -100 if self.debts else 100
        return max(0, min(1000, int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))))


@dataclass(frozen=True)
class CreditRequest:
    request_id: str
    cpf: str
    timestamp: str
    current_limit: Decimal
    requested_limit: Decimal
    status: str


@dataclass(frozen=True)
class Quote:
    currency: str
    rate: Decimal
    observed_at: str
    source: str
    simulated: bool = False


@dataclass(frozen=True)
class Intent:
    name: str
    currency: str = "USD"
    input_tokens: int = 0
    output_tokens: int = 0
    usage_known: bool = True
