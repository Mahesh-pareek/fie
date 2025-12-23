from fie.core.transaction import Transaction

CATEGORY_MAP = {
    "f": "food",
    "c": "coffee",
    "o": "outing",
    "t": "travel",
    "n": "noise",
}


def edit_transaction_tag(txn: Transaction) -> Transaction:
    if txn.amount < 20:
        print("Micro-transaction (<₹20). Tag editing is disabled.")
        return txn

    print("\n-----------------------------")
    print(f"Date        : {txn.datetime.date()}")
    print(f"Amount      : ₹{txn.amount}")
    print(f"Current cat : {txn.category}")
    print("-----------------------------")

    cat_in = input("New Category [f c o t]: ").strip().lower()

    if not cat_in or cat_in not in CATEGORY_MAP:
        print("No change made.")
        return txn

    return Transaction(
        **{
            **txn.__dict__,
            "category": [CATEGORY_MAP[cat_in]],
            "reviewed": True,
        }
    )
