from typing import List
from fie.core.transaction import Transaction
from fie.tagging.review import review_transactions


def edit_transactions(txns: List[Transaction]) -> List[Transaction]:
    eligible = [t for t in txns if t.amount >= 20]

    if not eligible:
        print("No editable transactions (micro-transactions skipped).")
        return []

    print(f"Editing {len(eligible)} transactions")
    return review_transactions(eligible)
