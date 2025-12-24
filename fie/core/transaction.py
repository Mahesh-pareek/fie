from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List
import hashlib


@dataclass(frozen=True)
class Transaction:
    # ---------------- KEY FIELDS ----------------
    id: str
    datetime: datetime
    amount: float
    direction: str              # "credit" | "debit"
    counterparty: str
    mode: str                   # UPI | IMPS | CASH | INTERNAL | UNKNOWN

    # ---------------- WORKFLOW STATE ----------------
    reviewed: bool = False

    # ---------------- CLASSIFICATION ----------------
    scope: str = "unknown"
    category: List[str] = field(default_factory=list)

    # ---------------- EXTRA METADATA ----------------
    extras: Dict = field(default_factory=dict)

    def __post_init__(self):
        if self.amount <= 0:
            raise ValueError("Amount must be positive")
        if self.direction not in ("credit", "debit"):
            raise ValueError("Invalid direction")

    @staticmethod
    def compute_id(
        datetime: datetime,
        amount: float,
        direction: str,
        counterparty: str,
        mode: str,
        raw_txn: str,
        source_file: str,
    ) -> str:
        raw = (
            f"{datetime.isoformat()}|"
            f"{amount}|"
            f"{direction}|"
            f"{counterparty}|"
            f"{mode}|"
            f"{raw_txn}|"
            f"{source_file}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "datetime": self.datetime.isoformat(),
            "amount": self.amount,
            "direction": self.direction,
            "counterparty": self.counterparty,
            "mode": self.mode,
            "reviewed": self.reviewed,
            "scope": self.scope,
            "category": self.category,
            "extras": self.extras,
        }
