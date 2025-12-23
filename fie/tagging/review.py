from typing import List
from fie.core.transaction import Transaction
from fie import config

SCOPE_MAP = config.get("tagging.scope_map")
CATEGORY_MAP = config.get("tagging.category_map")


def review_transactions(txns: List[Transaction]) -> List[Transaction]:
    reviewed = []

    for i, txn in enumerate(txns):
        print("\n-----------------------------")
        print(f"[{i+1}/{len(txns)}] ID: {txn.id[:12]}")
        print(f"Date        : {txn.datetime.date()}")
        print(f"Amount      : {'-' if txn.direction=='debit' else '+'}₹{txn.amount}")
        print(f"Direction   : {txn.direction}")
        print(f"Counterparty: {txn.counterparty}")
        print("-----------------------------")

        scope_in = input("Scope [p/f/e/s/S=skip] (Enter = keep): ").strip().lower()
        
        if scope_in == "s":
            continue

        scope = txn.scope if scope_in == "" else SCOPE_MAP.get(scope_in, txn.scope)

        cat_in = input(
            "Category [f=food c=coffee o=outing t=travel] (Enter = keep): "
        ).strip().lower()

        if cat_in == "":
            category = txn.category
        else:
            category = []
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
