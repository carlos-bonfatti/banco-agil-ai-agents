import csv
import fcntl
import os
import tempfile
from contextlib import contextmanager
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from banco_agil.domain import Client, CreditRequest, DomainError, InfrastructureError

CLIENT_FIELDS = ["cpf", "nome", "data_nascimento", "limite_credito", "score"]
SCORE_FIELDS = ["score_min", "score_max", "limite_maximo"]
REQUEST_FIELDS = [
    "request_id",
    "cpf_cliente",
    "data_hora_solicitacao",
    "limite_atual",
    "novo_limite_solicitado",
    "status_pedido",
]


class CsvRepository:
    """CSV local com lock entre processos e substituição atômica por arquivo.

    Crédito aprovado registra uma decisão; não altera limite disponível.
    Isso evita simular uma efetivação bancária que o enunciado não especifica.
    O lock requer filesystem local POSIX; não usar em deploy distribuído.
    """

    def __init__(self, directory: Path):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _locked(self):
        with (self.directory / ".bank.lock").open("a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def _read(self, name: str) -> list[dict[str, str]]:
        try:
            with (self.directory / name).open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                fields = {
                    "clientes.csv": CLIENT_FIELDS,
                    "score_limite.csv": SCORE_FIELDS,
                    "solicitacoes_aumento_limite.csv": REQUEST_FIELDS,
                }[name]
                if (
                    reader.fieldnames is None
                    or len(reader.fieldnames) != len(fields)
                    or set(reader.fieldnames) != set(fields)
                ):
                    raise ValueError("invalid columns")
                rows = list(reader)
                if any(set(row) != set(fields) or None in row.values() for row in rows):
                    raise ValueError("invalid row")
                identity = {
                    "clientes.csv": "cpf",
                    "solicitacoes_aumento_limite.csv": "request_id",
                }.get(name)
                if identity and len({row[identity] for row in rows}) != len(rows):
                    raise ValueError("duplicate identity")
                return rows
        except (OSError, csv.Error, ValueError) as exc:
            raise InfrastructureError("Não foi possível acessar a base de dados.") from exc

    def _write(self, name: str, fields: list[str], rows: list[dict[str, str]]) -> None:
        target = self.directory / name
        fd, temporary = tempfile.mkstemp(dir=self.directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    @staticmethod
    def _stored_money(value: str) -> Decimal:
        number = Decimal(value)
        if not number.is_finite() or not 0 <= number <= Decimal("1000000000"):
            raise ValueError("invalid stored money")
        if number != number.quantize(Decimal("0.01")):
            raise ValueError("invalid precision")
        return number

    @staticmethod
    def _client(row: dict[str, str]) -> Client:
        try:
            score = int(row["score"])
            if not 0 <= score <= 1000:
                raise ValueError("invalid stored score")
            return Client(
                row["cpf"],
                row["nome"],
                date.fromisoformat(row["data_nascimento"]),
                CsvRepository._stored_money(row["limite_credito"]),
                score,
            )
        except (ValueError, ArithmeticError) as exc:
            raise InfrastructureError("Cadastro inválido na base de dados.") from exc

    def authenticate(self, cpf: str, birth: date) -> Client | None:
        with self._locked():
            for row in self._read("clientes.csv"):
                if row["cpf"] == cpf and row["data_nascimento"] == birth.isoformat():
                    return self._client(row)
        return None

    def client(self, cpf: str) -> Client:
        with self._locked():
            return self._client(self._find(self._read("clientes.csv"), cpf))

    @staticmethod
    def _find(rows: list[dict[str, str]], cpf: str) -> dict[str, str]:
        for row in rows:
            if row["cpf"] == cpf:
                return row
        raise DomainError("Cliente não encontrado.")

    def update_score(self, cpf: str, score: int) -> None:
        if not 0 <= score <= 1000:
            raise DomainError("Score inválido.")
        with self._locked():
            rows = self._read("clientes.csv")
            self._find(rows, cpf)["score"] = str(score)
            self._write("clientes.csv", CLIENT_FIELDS, rows)

    @staticmethod
    def _request(row: dict[str, str]) -> CreditRequest:
        try:
            if row["status_pedido"] not in {"aprovado", "rejeitado"}:
                raise ValueError("invalid stored status")
            if datetime.fromisoformat(row["data_hora_solicitacao"]).tzinfo is None:
                raise ValueError("missing timezone")
            return CreditRequest(
                row["request_id"],
                row["cpf_cliente"],
                row["data_hora_solicitacao"],
                CsvRepository._stored_money(row["limite_atual"]),
                CsvRepository._stored_money(row["novo_limite_solicitado"]),
                row["status_pedido"],
            )
        except (ValueError, ArithmeticError) as exc:
            raise InfrastructureError("Pedido inválido na base de dados.") from exc

    @staticmethod
    def _bands(rows: list[dict[str, str]]) -> list[tuple[int, int, Decimal]]:
        try:
            bands = sorted(
                (
                    int(row["score_min"]),
                    int(row["score_max"]),
                    CsvRepository._stored_money(row["limite_maximo"]),
                )
                for row in rows
            )
            next_score = 0
            for lower, upper, _ in bands:
                if lower != next_score or not lower <= upper <= 1000:
                    raise ValueError("overlap or gap")
                next_score = upper + 1
            if next_score != 1001:
                raise ValueError("incomplete bands")
            return bands
        except (ValueError, ArithmeticError) as exc:
            raise InfrastructureError("Tabela de crédito inválida.") from exc

    def request_credit(self, cpf: str, amount: Decimal, request_id: str) -> CreditRequest:
        if not request_id or len(request_id) > 128:
            raise DomainError("Identificador de solicitação inválido.")
        if not amount.is_finite() or amount <= 0 or amount > Decimal("1000000000"):
            raise DomainError("Limite solicitado inválido.")
        if amount != amount.quantize(Decimal("0.01")):
            raise DomainError("Use no máximo duas casas decimais.")
        with self._locked():
            requests = self._read("solicitacoes_aumento_limite.csv")
            for row in requests:
                if row["request_id"] == request_id:
                    existing = self._request(row)
                    if existing.cpf != cpf or existing.requested_limit != amount:
                        raise DomainError("Solicitação já usada com dados diferentes.")
                    return existing
            client = self._client(self._find(self._read("clientes.csv"), cpf))
            if amount <= client.limit:
                raise DomainError("O novo limite deve ser maior que o limite atual.")
            bands = self._bands(self._read("score_limite.csv"))
            matches = [maximum for lower, upper, maximum in bands if lower <= client.score <= upper]
            if len(matches) != 1:
                raise InfrastructureError("Tabela de crédito inválida para este score.")
            row = {
                "request_id": request_id,
                "cpf_cliente": cpf,
                "data_hora_solicitacao": datetime.now(timezone.utc).isoformat(),
                "limite_atual": str(client.limit),
                "novo_limite_solicitado": str(amount),
                "status_pedido": "aprovado" if amount <= matches[0] else "rejeitado",
            }
            requests.append(row)
            self._write("solicitacoes_aumento_limite.csv", REQUEST_FIELDS, requests)
            return self._request(row)
