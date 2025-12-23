from typing import List
from fie.core.transaction import Transaction

SCOPE_MAP = {
    "p": "personal",
    "f": "family",
    "e": "education",
    "s": "shared",
}

CATEGORY_MAP = {
    "f": "food",
    "c": "coffee",
    "o": "outing",
    "t": "travel",
    "n": "noise",
}


def review_transactions(txns: List[Transaction]) -> List[Transaction]:
    reviewed = []

    for txn in txns:
        print("\n-----------------------------")
        print(f"Date        : {txn.datetime.date()}")
        print(f"Amount      : {'-' if txn.direction=='debit' else '+'}₹{txn.amount}")
        print(f"Direction   : {txn.direction}")
        print(f"Counterparty: {txn.counterparty}")
        print("-----------------------------")

        scope_in = input("Scope [p/f/e/s]: ").strip().lower()
        scope = SCOPE_MAP.get(scope_in, txn.scope)

        cat_in = input(
            "Category [f=food c=coffee o=outing t=travel]: "
        ).strip().lower()

        category = []
        if cat_in:
            for c in cat_in.split(","):
                if c.strip() in CATEGORY_MAP:
                    category.append(CATEGORY_MAP[c.strip()])

        reviewed.append(
            Transaction(
                **{
                    **txn.__dict__,
                    "scope": scope,
                    "category": category,
                    "reviewed": True,
                }
            )
        )

    return reviewed
