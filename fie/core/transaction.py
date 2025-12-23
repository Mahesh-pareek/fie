from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import hashlib


@dataclass(frozen=True)
class Transaction:
    id: str
    datetime: datetime
    amount: float
    direction: str         
    counterparty: str       
    mode: str              
    reference: Optional[str]
    upi_id: Optional[str]
    source_file: str

    scope: str = "unknown"
    category: List[str] = field(default_factory=list)
    reviewed: bool = False

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
        reference: Optional[str],
        source_file: str,
    ) -> str:
        raw = (
            f"{datetime.isoformat()}|"
            f"{amount}|"
            f"{direction}|"
            f"{counterparty}|"
            f"{mode}|"
            f"{reference}|"
            f"{source_file}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()
