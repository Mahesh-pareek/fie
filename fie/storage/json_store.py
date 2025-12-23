import json
from pathlib import Path
from typing import List
from datetime import datetime

from fie.core.transaction import Transaction
from fie.storage.base import TransactionStore


class JsonTransactionStore(TransactionStore):
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"transactions": []})

    def _read(self):
        with open(self.path, "r") as f:
            return json.load(f)

    def _write(self, data):
        tmp = self.path.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        tmp.replace(self.path)

    def add(self, txns: List[Transaction]) -> None:
        data = self._read()
        existing_ids = {t["id"] for t in data["transactions"]}

        for txn in txns:
            if txn.id not in existing_ids:
                data["transactions"].append(self._serialize(txn))

        self._write(data)

    def update(self, txns: List[Transaction]) -> None:
        data = self._read()
        tx_map = {txn.id: txn for txn in txns}

        updated = []
        for t in data["transactions"]:
            if t["id"] in tx_map:
                updated.append(self._serialize(tx_map[t["id"]]))
            else:
                updated.append(t)

        data["transactions"] = updated
        self._write(data)

    def list_all(self) -> List[Transaction]:
        data = self._read()
        return [self._deserialize(t) for t in data["transactions"]]

    # ---------- helpers ----------

    def _serialize(self, txn: Transaction) -> dict:
        d = txn.__dict__.copy()
        d["datetime"] = txn.datetime.isoformat()
        return d

    def _deserialize(self, data: dict) -> Transaction:
        d = data.copy()
        d["datetime"] = datetime.fromisoformat(d["datetime"])
        return Transaction(**d)
