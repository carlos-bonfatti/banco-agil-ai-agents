import json
import threading
import time
from datetime import datetime, timezone
from decimal import Decimal
from urllib.error import URLError
from urllib.request import urlopen

from banco_agil.domain import DomainError, InfrastructureError, Quote

ALLOWED = {"USD", "EUR", "GBP"}


class DemoExchange:
    def quote(self, currency: str) -> Quote:
        if currency not in ALLOWED:
            raise DomainError("Moeda não suportada. Use USD, EUR ou GBP.")
        return Quote(
            currency,
            {"USD": Decimal("5.00"), "EUR": Decimal("5.50"), "GBP": Decimal("6.50")}[currency],
            datetime.now(timezone.utc).isoformat(),
            "Demonstração",
            True,
        )


class AwesomeExchange:
    """Cache por processo com TTL; timeout único e sem retries ilimitados."""

    def __init__(self, ttl: float = 60):
        self.ttl = ttl
        self.cache: dict[str, tuple[float, Quote]] = {}
        self.locks = {currency: threading.Lock() for currency in ALLOWED}
        self.metrics = {"external_calls": 0, "cache_hits": 0, "errors": 0}
        self.metrics_lock = threading.Lock()

    def _count(self, name: str) -> None:
        with self.metrics_lock:
            self.metrics[name] += 1

    def quote(self, currency: str) -> Quote:
        if currency not in ALLOWED:
            raise DomainError("Moeda não suportada. Use USD, EUR ou GBP.")
        with self.locks[currency]:
            now = time.monotonic()
            cached = self.cache.get(currency)
            if cached and now - cached[0] < self.ttl:
                self._count("cache_hits")
                return cached[1]
            try:
                self._count("external_calls")
                with urlopen(
                    f"https://economia.awesomeapi.com.br/last/{currency}-BRL", timeout=4
                ) as response:
                    payload = json.loads(response.read(65536))
                if not isinstance(payload, dict):
                    raise ValueError("invalid payload")
                item = payload[f"{currency}BRL"]
                if not isinstance(item, dict):
                    raise ValueError("invalid item")
                if not isinstance(item.get("bid"), str) or not isinstance(
                    item.get("timestamp"), str
                ):
                    raise ValueError("invalid quote fields")
                rate = Decimal(item["bid"])
                if not rate.is_finite() or rate <= 0:
                    raise ValueError("invalid rate")
                stamp = datetime.fromtimestamp(int(item["timestamp"]), timezone.utc)
                if abs((datetime.now(timezone.utc) - stamp).total_seconds()) > 259200:
                    raise ValueError("stale quote")
                quote = Quote(currency, rate, stamp.isoformat(), "AwesomeAPI")
            except (URLError, OSError, ValueError, KeyError, TypeError, ArithmeticError) as exc:
                self._count("errors")
                raise InfrastructureError(
                    "Cotação indisponível. Tente novamente mais tarde."
                ) from exc
            self.cache[currency] = (time.monotonic(), quote)
            return quote
