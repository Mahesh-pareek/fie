from typing import List
from fie.core.transaction import Transaction
from fie.tagging.review import review_transactions
from fie import config


def edit_transactions(txns: List[Transaction]) -> List[Transaction]:
    min_edit_amount = config.get("tagging.edit_min_amount")
    eligible = [t for t in txns if t.amount >= min_edit_amount]

    if not eligible:
        print("No editable transactions (micro-transactions skipped).")
        return []

    print(f"\nEditing {len(eligible)} transactions")
    print("Tip: Press 's' to skip current transaction, Enter to keep existing values.")
    print("Use 'fie edit --id <ID>' for single-transaction edits.\n")

    return review_transactions(eligible)
