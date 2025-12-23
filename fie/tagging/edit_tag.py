from fie.core.transaction import Transaction
from fie import config

CATEGORY_MAP = config.get("tagging.category_map")


def edit_transaction_tag(txn: Transaction) -> Transaction:
    min_edit_amount = config.get("tagging.edit_min_amount")
    
    if txn.amount < min_edit_amount:
        print(f"Micro-transaction (<₹{min_edit_amount}). Tag editing is disabled.")
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
