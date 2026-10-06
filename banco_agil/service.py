from decimal import Decimal

from banco_agil.domain import CreditRequest, DomainError, Interview
from banco_agil.ports import BankingRepository
from banco_agil.session import Session


class BankingService:
    """Todas as ferramentas exigem uma sessão; o modelo não escolhe um CPF."""

    def __init__(self, repository: BankingRepository):
        self.repository = repository

    def limit(self, session: Session) -> Decimal:
        return self.repository.client(session.authenticated_cpf()).limit

    def request(self, session: Session, amount: Decimal, event_id: str) -> CreditRequest:
        return self.repository.request_credit(
            session.authenticated_cpf(), amount, f"{session.session_id}:{event_id}"
        )

    def interview(self, session: Session, interview: Interview) -> int:
        if session.stage != "debts":
            raise DomainError("Entrevista fora da etapa permitida.")
        cpf = session.authenticated_cpf()
        score = interview.score()
        self.repository.update_score(cpf, score)
        return score
