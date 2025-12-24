import json
from pathlib import Path
from typing import List
from datetime import datetime

from fie.core.transaction import Transaction
from fie.storage.base import TransactionStore


class JsonTransactionStore(TransactionStore):
    def __init__(self, path: Path):
        self.path = path
        self._init_store()

    # ---------- lifecycle ----------

    def _init_store(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"transactions": []})

    # ---------- core IO ----------

    def _read(self):
        try:
            with open(self.path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            # File deleted mid-run → recreate
            self._init_store()
            return {"transactions": []}
        except json.JSONDecodeError:
            # Corrupted file → reset safely
            self._write({"transactions": []})
            return {"transactions": []}

    def _write(self, data):
        tmp = self.path.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        tmp.replace(self.path)

    # ---------- public API ----------

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
        # Prefer the model's explicit serializer when available.
        if hasattr(txn, "to_dict"):
            return txn.to_dict()

        d = txn.__dict__.copy()
        d["datetime"] = txn.datetime.isoformat()
        return d

    def _deserialize(self, data: dict) -> Transaction:
        d = data.copy()

        # ---- datetime ----
        if isinstance(d.get("datetime"), str):
            d["datetime"] = datetime.fromisoformat(d["datetime"])

        # ---- legacy compatibility ----
        extras = d.get("extras")
        if not isinstance(extras, dict):
            extras = {}

        # Older schema stored these at top-level; move to extras.
        for legacy_key in ("reference", "upi_id", "source_file", "balance", "chq_id", "raw_txn"):
            if legacy_key in d:
                extras.setdefault(legacy_key, d.pop(legacy_key))

        d["extras"] = extras
        d.setdefault("mode", extras.get("mode") or "UNKNOWN")

        if d.get("category") is None:
            d["category"] = []

        # Drop unknown keys to avoid crashing on old/new schema drift.
        allowed = set(Transaction.__dataclass_fields__.keys())
        d = {k: v for k, v in d.items() if k in allowed}

        return Transaction(**d)
