from fie.core.transaction import Transaction


def apply_micro_rules(txn: Transaction) -> Transaction:
    """
    Deterministic micro-transaction rules.
    """

    amount = txn.amount

    if amount <= 10:
        return Transaction(
            **{
                **txn.__dict__,
                "scope": "personal",
                "category": ["noise"],
                "reviewed": True,
            }
        )

    if 11 <= amount <= 20:
        return Transaction(
            **{
                **txn.__dict__,
                "scope": "personal",
                "category": ["coffee"],
                "reviewed": True,
            }
        )

    return txn
