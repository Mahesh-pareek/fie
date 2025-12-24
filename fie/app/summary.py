# fie/app/summary.py

from collections import defaultdict
from fie import config


def signed_amount(txn):
    return txn.amount if txn.direction == "credit" else -txn.amount


def fmt_amount_fixed(amount, width=14):
    sign = "-" if amount < 0 else ""
    return f"{sign}{abs(amount):,.2f}₹".rjust(width)


def aggregate(txns, key, all_keys=None):
    counts = defaultdict(int)
    totals = defaultdict(float)

    for txn in txns:
        value = getattr(txn, key)
        if key == "category":
            value = value[0] if value else "unknown"

        counts[value] += 1
        totals[value] += signed_amount(txn)

    if all_keys:
        for k in all_keys:
            counts.setdefault(k, 0)
            totals.setdefault(k, 0.0)

    return counts, totals


def print_agg(title, counts, totals):
    print(title)
    print("=" * len(title))
    print(f"{'Key':<12} {'Count':<8} {'Net Amount':>14}")
    print("-" * 36)

    net = 0.0
    for k in sorted(counts):
        net += totals[k]
        print(
            f"{k:<12} {counts[k]:<8} {fmt_amount_fixed(totals[k])}"
        )

    print("-" * 36)
    print(f"{'NET':<20} {fmt_amount_fixed(net)}")
    print()


def run(args, engine):
    txns = engine.all()

    print("Transaction Summary")
    print("===================")
    print(f"Total Transactions : {len(txns)}")
    print()

    # ---- Category summary ----
    cat_counts, cat_totals = aggregate(txns, "category")
    print_agg("Summary by Category", cat_counts, cat_totals)

    # ---- Scope summary ----
    scopes = config.get("tagging.scope_map").values()
    scope_counts, scope_totals = aggregate(txns, "scope", scopes)
    print_agg("Summary by Scope", scope_counts, scope_totals)
