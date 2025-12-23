from typing import List
from fie.core.transaction import Transaction
from fie.core.rules import apply_micro_rules
from fie.storage.base import TransactionStore


class FIEEngine:
    def __init__(self, store: TransactionStore):
        self.store = store

    def ingest(self, txns: List[Transaction]) -> None:
        processed = [apply_micro_rules(txn) for txn in txns]
        self.store.add(processed)

    def all(self) -> List[Transaction]:
        return self.store.list_all()

    def unreviewed(self) -> List[Transaction]:
        return [t for t in self.store.list_all() if not t.reviewed]
