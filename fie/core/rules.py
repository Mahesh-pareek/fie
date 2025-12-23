from fie.core.transaction import Transaction
from fie import config


def apply_micro_rules(txn: Transaction) -> Transaction:
    """
    Deterministic micro-transaction rules.
    """
    rules = config.get("rules.micro_transaction")
    noise_max = rules["noise_max_amount"]
    coffee_min = rules["coffee_min_amount"]
    coffee_max = rules["coffee_max_amount"]

    amount = txn.amount

    if amount <= noise_max:
        return Transaction(
            **{
                **txn.__dict__,
                "scope": "personal",
                "category": ["noise"],
                "reviewed": True,
            }
        )

    if coffee_min <= amount <= coffee_max:
        return Transaction(
            **{
                **txn.__dict__,
                "scope": "personal",
                "category": ["coffee"],
                "reviewed": True,
            }
        )

    return txn
