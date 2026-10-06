from dataclasses import dataclass, field
from decimal import Decimal
from threading import RLock
from time import monotonic
from uuid import uuid4

from banco_agil.domain import DomainError


@dataclass
class Session:
    session_id: str = field(default_factory=lambda: str(uuid4()))
    stage: str = "cpf"
    cpf: str | None = None
    pending_cpf: str | None = None
    failures: int = 0
    interview: dict = field(default_factory=dict)
    desired_limit: Decimal | None = None
    last_activity: float = field(default_factory=monotonic)
    idle_timeout_seconds: float = 900
    llm_calls: int = 0
    # Respostas deduplicadas só em memória; não é persistência distribuída.
    responses: dict[str, tuple[str, str]] = field(default_factory=dict)
    lock: RLock = field(default_factory=RLock, repr=False)

    def authenticated_cpf(self) -> str:
        if self.cpf is not None and monotonic() - self.last_activity >= self.idle_timeout_seconds:
            self.close()
            raise DomainError("Sua sessão expirou por inatividade. Inicie uma nova conversa.")
        if self.cpf is None or self.stage == "closed":
            raise DomainError("Autenticação necessária.")
        return self.cpf

    def close(self) -> None:
        self.stage = "closed"
        self.cpf = None
        self.pending_cpf = None
        self.interview.clear()
        self.desired_limit = None
        self.responses.clear()
