import argparse
from datetime import datetime
from pathlib import Path

from fie.core.transaction import Transaction
from fie.core.engine import FIEEngine
from fie.storage.json_store import JsonTransactionStore
from fie.tagging.review import review_transactions
from fie.analysis.summary import personal_expense_summary,scope_wise_summary
from fie.report.printer import print_summary
from fie.ingest.canara import parse_canara_pdf
from fie.tagging.edit import edit_transactions


DATA_PATH = Path.home() / ".fie" / "transactions.json"


def main():
    parser = argparse.ArgumentParser(
        prog="fie",
        description="FIE — Financial Intelligence Engine (Stage 1)",
    )

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("ingest-pdf", help="Ingest Canara Bank PDF")
    subparsers.add_parser("ingest-demo", help="Ingest demo transactions")
    subparsers.add_parser("review", help="Review untagged transactions")
    subparsers.add_parser("summary", help="Show personal expense summary")
    subparsers.add_parser("scope-summary", help="Show scope-wise net summary")
    list_parser = subparsers.add_parser("list", help="List transactions")
    list_parser.add_argument("--sort", choices=["date", "amount", "scope", "counterparty"], default="date")
    list_parser.add_argument("--scope", help="Filter by scope (personal/family/education/shared)")
    list_parser.add_argument("--cat", help="Filter by category")
    list_parser.add_argument("--dir", choices=["debit", "credit"], help="Filter by direction")
    edit_parser = subparsers.add_parser("edit", help="Edit existing transactions")
    edit_parser.add_argument("--id", help="Edit transaction by ID")
    edit_parser.add_argument("--scope", help="Filter by scope")
    edit_parser.add_argument("--cat", help="Filter by category")

    args = parser.parse_args()

    store = JsonTransactionStore(DATA_PATH)
    engine = FIEEngine(store)

    if args.command == "ingest-demo":
        demo_txns = [
            Transaction(
                id="demo-1",
                datetime=datetime.now(),
                amount=10,
                direction="debit",
                counterparty="Tea Stall",
                reference=None,
                upi_id=None,
                source_file="demo",
            ),
            Transaction(
                id="demo-2",
                datetime=datetime.now(),
                amount=120,
                direction="debit",
                counterparty="Groceries",
                reference=None,
                upi_id=None,
                source_file="demo",
            ),
        ]
        engine.ingest(demo_txns)
        print("Demo transactions ingested.")

    elif args.command == "ingest-pdf":
        pdf_path = input("Path to Canara PDF: ").strip()
        txns = parse_canara_pdf(pdf_path)
        engine.ingest(txns)
        print(f"Ingested {len(txns)} transactions.")

    elif args.command == "review":
        pending = engine.unreviewed()
        if not pending:
            print("No transactions to review.")
            return

        reviewed = review_transactions(pending)
        store.update(reviewed)
        print(f"Reviewed {len(reviewed)} transactions.")

    elif args.command == "summary":
        txns = engine.all()
        summary = personal_expense_summary(txns)
        print_summary("Personal Expenses", summary)

    elif args.command == "list":
        txns = engine.all()

        # ---------- filters ----------
        if args.scope:
            txns = [t for t in txns if t.scope == args.scope]

        if args.dir:
            txns = [t for t in txns if t.direction == args.dir]

        if args.cat:
            txns = [t for t in txns if args.cat in t.category]

        # ---------- sorting ----------
        if args.sort == "date":
            txns.sort(key=lambda t: t.datetime)
        elif args.sort == "amount":
            txns.sort(key=lambda t: t.amount)
        elif args.sort == "scope":
            txns.sort(key=lambda t: t.scope)
        elif args.sort == "counterparty":
            txns.sort(key=lambda t: t.counterparty)

        # ---------- display ----------
        for t in txns:
            sign = "-" if t.direction == "debit" else "+"
            cats = ",".join(t.category) if t.category else "-"
            print(
                f"{t.datetime.date()} | {sign}₹{t.amount:<8} | "
                f"{t.scope:<9} | {cats:<10} | {t.counterparty}"
            )

    elif args.command == "scope-summary":
        txns = engine.all()
        summary = scope_wise_summary(txns)
        print_summary("Scope-wise Summary", summary)

    elif args.command == "edit":
        txns = engine.all()

        if args.id:
            txns = [t for t in txns if t.id == args.id]

        if args.scope:
            txns = [t for t in txns if t.scope == args.scope]

        if args.cat:
            txns = [t for t in txns if args.cat in t.category]

        if not txns:
            print("No matching transactions to edit.")
            return

        edited = edit_transactions(txns)
        store.update(edited)
        print(f"Edited {len(edited)} transactions.")


    else:
        parser.print_help()
