# fie/app/edit.py

from fie import config


def fmt_amount(amount, direction):
    sign = "-" if direction == "debit" else "+"
    return f"{sign}₹{amount:,.2f}"


def print_txn_header(idx, total, txn):
    print("-" * 50)
    print(f"[{idx}/{total}] ID: {txn.id[:12]}")
    print(f"Date        : {txn.datetime.strftime('%Y-%m-%d %H:%M')}")
    print(f"Amount      : {fmt_amount(txn.amount, txn.direction)}")
    print(f"Counterparty: {txn.counterparty}")
    print("Current")
    print(f"  Scope     : {txn.scope}")
    print(f"  Category  : {', '.join(txn.category) if txn.category else '-'}")
    print("-" * 50)


def run(args, engine, store):
    txns = engine.all()

    rules = config.get("tagging")
    min_amt = rules["edit_min_amount"]
    scope_map = rules["scope_map"]
    category_map = rules["category_map"]

    # ---- only unreviewed & meaningful txns ----
    txns = [
        t for t in txns
        if not t.reviewed and abs(t.amount) >= min_amt
    ]

    if not txns:
        print("✓ No transactions require review.")
        return

    edited = []

    print(f"Editing {len(txns)} transactions")
    print("Tip: x = skip | Enter = keep existing\n")

    for i, txn in enumerate(txns, 1):
        original_scope = txn.scope
        original_category = list(txn.category)

        print_txn_header(i, len(txns), txn)

        # ---------------- Scope ----------------
        scope_prompt = (
            "Scope "
            "[p=personal / f=family / e=education / s=shared / x=skip] "
            "(Enter=keep): "
        )
        scope_in = input(scope_prompt).strip().lower()

        if scope_in == "x":
            print("↷ Skipped\n")
            continue

        if scope_in in scope_map:
            txn.scope = scope_map[scope_in]

        # ---------------- Category ----------------
        cat_prompt = (
            "Category "
            "[f=food c=coffee o=outing t=travel n=noise] "
            "(comma allowed, Enter=keep): "
        )
        cat_in = input(cat_prompt).strip().lower()

        if cat_in:
            cats = []
            for c in cat_in.split(","):
                c = c.strip()
                if c in category_map:
                    cats.append(category_map[c])
            txn.category = cats

        # ---------------- Review flag ----------------
        if txn.scope != original_scope or txn.category != original_category:
            txn.reviewed = True
            edited.append(txn)
            print("✓ Updated\n")
        else:
            print("✓ No change\n")

    if edited:
        store.update(edited)
        print(f"✓ Updated {len(edited)} transaction(s).")
    else:
        print("✓ No changes made.")
