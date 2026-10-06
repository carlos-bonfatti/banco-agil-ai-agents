from datetime import date
from decimal import Decimal
from typing import Protocol

from banco_agil.domain import Client, CreditRequest, Intent, Quote


class BankingRepository(Protocol):
    """Fronteira transacional: substituível por PostgreSQL ou um serviço remoto."""

    def authenticate(self, cpf: str, birth: date) -> Client | None: ...
    def client(self, cpf: str) -> Client: ...
    def update_score(self, cpf: str, score: int) -> None: ...
    def request_credit(self, cpf: str, amount: Decimal, request_id: str) -> CreditRequest: ...


class IntentInterpreter(Protocol):
    """O modelo só classifica intenção; não possui permissão para executar operações."""

    def interpret(self, message: str) -> Intent: ...


class ExchangeProvider(Protocol):
    def quote(self, currency: str) -> Quote: ...


class KnowledgeSearch(Protocol):
    """Extensão futura: recuperação de conteúdo com filtro de acesso obrigatório.

    Contrato definido; nenhum banco vetorial é utilizado pelo desafio atual.
    Não usar esta fronteira para autenticação, saldo ou decisões de crédito.
    """

    def search(self, query: str, *, scope: str, limit: int = 5) -> list[dict[str, str]]: ...
