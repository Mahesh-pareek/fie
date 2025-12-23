from collections import defaultdict
from typing import Dict, List
from fie.core.transaction import Transaction


def personal_expense_summary(txns: List[Transaction]) -> Dict[str, float]:
    summary = defaultdict(float)

    for txn in txns:
        if txn.scope != "personal":
            continue

        sign = -1 if txn.direction == "debit" else 1
        categories = txn.category or ["uncategorized"]

        for cat in categories:
            summary[cat] += sign * txn.amount

    return dict(summary)

def scope_wise_summary(txns):
    """
    Net amount per scope.
    debit  -> negative
    credit -> positive
    """
    summary = {}

    for txn in txns:
        scope = txn.scope or "unknown"
        sign = -1 if txn.direction == "debit" else 1

        summary.setdefault(scope, 0.0)
        summary[scope] += sign * txn.amount

    return summary

def filter_by_scope(txns, scope):
    return [t for t in txns if t.scope == scope]
