from typing import List
from fie.core.transaction import Transaction
from fie.tagging.review import review_transactions


def edit_transactions(txns: List[Transaction]) -> List[Transaction]:
    """
    Re-review already stored transactions.
    Uses same UX as review.
    """
    print(f"Editing {len(txns)} transactions")
    return review_transactions(txns)
