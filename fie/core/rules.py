from fie.core.transaction import Transaction
from fie import config

def normalize_name_spacing(s: str) -> str:
    """
    Join alphabetic tokens, preserve spacing for anything involving digits.
    """
    tokens = s.split()

    # if every token is alphabetic → join everything
    if all(tok.isalpha() for tok in tokens):
        return "".join(tokens)

    # otherwise, join only adjacent alphabetic tokens
    out = []
    i = 0
    n = len(tokens)

    while i < n:
        cur = tokens[i]

        if cur.isalpha():
            j = i + 1
            merged = cur

            while j < n and tokens[j].isalpha():
                merged += tokens[j]
                j += 1

            out.append(merged)
            i = j
        else:
            out.append(cur)
            i += 1

    return " ".join(out)



def apply_micro_rules(txn: Transaction) -> Transaction:
    """
    Deterministic micro-transaction rules + final normalization.
    """
    rules = config.get("rules.micro_transaction")
    noise_max = rules["noise_max_amount"]
    coffee_min = rules["coffee_min_amount"]
    coffee_max = rules["coffee_max_amount"]

    amount = txn.amount

    # ---- normalize counterparty (REMOVE SPACES) ----
    normalized_counterparty = normalize_name_spacing(txn.counterparty)

    # ---- clean extras ----
    extras = dict(txn.extras) if txn.extras else {}

    # keep only required fields
    extras = {
        "balance": extras.get("balance"),
        "chq_id": extras.get("chq_id"),
        "raw": extras.get("raw_nospace") or extras.get("raw"),
        "source_file": extras.get("source_file"),
    }

    # ---- noise ----
    if amount <= noise_max:
        return Transaction(
            **{
                **txn.__dict__,
                "counterparty": normalized_counterparty,
                "scope": "personal",
                "category": ["noise"],
                "reviewed": True,
                "extras": extras,
            }
        )

    # ---- coffee ----
    if coffee_min <= amount <= coffee_max:
        return Transaction(
            **{
                **txn.__dict__,
                "counterparty": normalized_counterparty,
                "scope": "personal",
                "category": ["coffee"],
                "reviewed": True,
                "extras": extras,
            }
        )

    # ---- default ----
    return Transaction(
        **{
            **txn.__dict__,
            "counterparty": normalized_counterparty,
            "extras": extras,
        }
    )
