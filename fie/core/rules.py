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
    Auto-categorizes small transactions:
      0-10  → noise
      11-25 → coffee
      26-50 → snacks
      51-100 → daily
    """
    rules = config.get("rules.micro_transaction")
    
    # Thresholds from config
    noise_max = rules.get("noise_max", 10)
    coffee_min = rules.get("coffee_min", 11)
    coffee_max = rules.get("coffee_max", 25)
    snacks_min = rules.get("snacks_min", 26)
    snacks_max = rules.get("snacks_max", 50)
    daily_min = rules.get("daily_min", 51)
    daily_max = rules.get("daily_max", 100)

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

    # Helper to create auto-tagged transaction
    def auto_tag(category: str) -> Transaction:
        return Transaction(
            **{
                **txn.__dict__,
                "counterparty": normalized_counterparty,
                "scope": "personal",
                "category": [category],
                "reviewed": True,
                "extras": extras,
            }
        )

    # ---- noise (0-10) ----
    if amount <= noise_max:
        return auto_tag("noise")

    # ---- coffee (11-25) ----
    if coffee_min <= amount <= coffee_max:
        return auto_tag("coffee")

    # ---- snacks (26-50) ----
    if snacks_min <= amount <= snacks_max:
        return auto_tag("snacks")

    # ---- daily (51-100) ----
    if daily_min <= amount <= daily_max:
        return auto_tag("daily")

    # ---- default (>100) - no auto-tagging ----
    return Transaction(
        **{
            **txn.__dict__,
            "counterparty": normalized_counterparty,
            "extras": extras,
        }
    )
