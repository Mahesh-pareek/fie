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
from fie.tagging.edit_tag import edit_transaction_tag
from fie import config


DATA_PATH = Path(config.get("storage.data_path"))


def main():
    parser = argparse.ArgumentParser(
        prog="fie",
        description="FIE — Financial Intelligence Engine (Stage 1)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  fie ingest-pdf          # Ingest transactions from Canara Bank PDF
  fie review              # Review untagged transactions
  fie list                # List all transactions
  fie list --scope personal --sort amount
  fie edit --id abc123    # Edit specific transaction
  fie edit-tag --id abc123
  fie summary -p          # Personal summary
  fie summary -a          # All summaries
  fie scope-summary       # Scope-wise summary
        """,
    )

    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # ========== INGEST COMMANDS ==========
    ingest_pdf_parser = subparsers.add_parser(
        "ingest-pdf",
        help="Ingest transactions from Canara Bank PDF",
        description="Parse a Canara Bank PDF statement and import transactions into the database."
    )
    ingest_pdf_parser.add_argument(
        "path",
        nargs="?",
        help="Path to PDF file. If not provided, you will be prompted to enter it interactively."
    )


    # ========== REVIEW COMMAND ==========
    subparsers.add_parser(
        "review",
        help="Review untagged transactions interactively",
        description="Interactively tag unreviewed transactions. Press 's' to skip, Enter to keep existing values."
    )

    # ========== LIST COMMAND ==========
    list_parser = subparsers.add_parser(
        "list",
        help="List transactions with filters and sorting",
        aliases=["ls"],
        description="Display all transactions with optional filtering and sorting. Use --limit to show fewer results."
    )
    list_parser.add_argument(
        "--sort",
        choices=["date", "amount", "scope", "counterparty"],
        default="date",
        help="Sort by field (default: date). Use 'amount' to sort by transaction amount, 'scope' for personal/family/etc."
    )
    list_parser.add_argument(
        "--scope",
        metavar="SCOPE",
        help="Filter by scope: personal, family, education, or shared. Only show transactions matching this scope."
    )
    list_parser.add_argument(
        "--category",
        metavar="CATEGORY",
        help="Filter by category (exact match): food, coffee, outing, travel, or noise."
    )
    list_parser.add_argument(
        "--direction",
        choices=["debit", "credit"],
        help="Filter by transaction direction: 'debit' for outgoing, 'credit' for incoming."
    )
    list_parser.add_argument(
        "--limit",
        type=int,
        metavar="N",
        help="Show only the first N transactions (useful for large datasets)."
    )

    # ========== EDIT COMMAND ==========
    edit_parser = subparsers.add_parser(
        "edit",
        help="Edit transaction tags interactively",
        description="Interactively edit tags for transactions matching your filters. Supports multiple filters (--id, --scope, --category)."
    )
    edit_parser.add_argument(
        "--id",
        metavar="ID",
        help="Edit transaction by ID prefix (partial match). E.g., '05c22e75' matches any transaction starting with these 8 characters. Use 'fie list' to find IDs."
    )
    edit_parser.add_argument(
        "--scope",
        metavar="SCOPE",
        help="Filter transactions by scope before editing. Scope: personal, family, education, or shared."
    )
    edit_parser.add_argument(
        "--category",
        metavar="CATEGORY",
        help="Filter transactions by category before editing. Category: food, coffee, outing, travel, or noise."
    )

    # ========== EDIT-TAG COMMAND ==========
    edit_tag_parser = subparsers.add_parser(
        "edit-tag",
        help="Edit single transaction tag by ID",
        description="Quickly edit the category tag for a specific transaction without interactive review."
    )
    edit_tag_parser.add_argument(
        "--id",
        required=True,
        metavar="ID",
        help="Transaction ID prefix (partial match supported). E.g., '05c22e75' finds the first transaction with this prefix. Get IDs from 'fie list' output (first column)."
    )

    # ========== SUMMARY COMMANDS ==========
    summary_parser = subparsers.add_parser(
        "summary",
        help="Show transaction summaries",
        aliases=["sum"],
        description="Display spending summaries by category or scope. Use flags to control what's shown."
    )
    summary_group = summary_parser.add_mutually_exclusive_group()
    summary_group.add_argument(
        "-a", "--all",
        action="store_true",
        help="Show all summaries: personal expenses by category AND scope-wise totals."
    )
    summary_group.add_argument(
        "-p", "--personal",
        action="store_true",
        help="Show only personal expense summary (breakdown by category: food, coffee, etc.)."
    )
    summary_group.add_argument(
        "-f", "--family",
        action="store_true",
        help="Show only family scope summary (total family transactions)."
    )
    summary_group.add_argument(
        "-e", "--education",
        action="store_true",
        help="Show only education scope summary (total education transactions)."
    )
    summary_group.add_argument(
        "-s", "--shared",
        action="store_true",
        help="Show only shared scope summary (total shared transactions)."
    )

    scope_summary_parser = subparsers.add_parser(
        "scope-summary",
        help="Show scope-wise net summary",
        description="Display net amount (debit - credit) for each scope: personal, family, education, shared."
    )

    args = parser.parse_args()

    store = JsonTransactionStore(DATA_PATH)
    engine = FIEEngine(store)

    if args.command == "ingest-pdf":
        pdf_path = args.path
        if not pdf_path:
            pdf_path = input("Path to Canara PDF: ").strip()
        
        if not Path(pdf_path).exists():
            print(f"✗ Error: File not found: {pdf_path}")
            return
        
        try:
            txns = parse_canara_pdf(pdf_path)
            engine.ingest(txns)
            print(f"✓ Ingested {len(txns)} transactions from {Path(pdf_path).name}")
        except Exception as e:
            print(f"✗ Error parsing PDF: {e}")
            return

    elif args.command == "review":
        pending = engine.unreviewed()
        if not pending:
            print("✓ No transactions to review.")
            return

        reviewed = review_transactions(pending)
        store.update(reviewed)
        print(f"✓ Reviewed {len(reviewed)} transactions.")

    elif args.command == "summary" or args.command == "sum":
        txns = engine.all()

        if args.all:
            print_summary("Personal Summary", personal_expense_summary(txns))
            print_summary("Scope-wise Summary", scope_wise_summary(txns))
        elif args.personal:
            print_summary("Personal Summary", personal_expense_summary(txns))
        elif args.family:
            summary = scope_wise_summary(txns)
            print_summary("Family Summary", {"family": summary.get("family", 0)})
        elif args.education:
            summary = scope_wise_summary(txns)
            print_summary("Education Summary", {"education": summary.get("education", 0)})
        elif args.shared:
            summary = scope_wise_summary(txns)
            print_summary("Shared Summary", {"shared": summary.get("shared", 0)})
        else:
            # default: scope-wise summary
            print_summary("Scope-wise Summary", scope_wise_summary(txns))

    elif args.command == "list" or args.command == "ls":
        txns = engine.all()

        # ---------- filters ----------
        if args.scope:
            txns = [t for t in txns if t.scope == args.scope]

        if args.direction:
            txns = [t for t in txns if t.direction == args.direction]

        if args.category:
            txns = [t for t in txns if args.category in t.category]

        # ---------- sorting ----------
        if args.sort == "date":
            txns.sort(key=lambda t: t.datetime)
        elif args.sort == "amount":
            txns.sort(key=lambda t: t.amount)
        elif args.sort == "scope":
            txns.sort(key=lambda t: t.scope)
        elif args.sort == "counterparty":
            txns.sort(key=lambda t: t.counterparty)

        # ---------- limit ----------
        if args.limit:
            txns = txns[:args.limit]

        # ---------- display ----------
        if not txns:
            print("No transactions to display.")
            return

        for t in txns:
            short_id = t.id[:12]
            cats = ",".join(t.category) if t.category else "-"
            sign = "-" if t.direction == "debit" else "+"
            print(
                f"{short_id} | {t.datetime.date()} | "
                f"{sign}₹{t.amount:<8.2f} | "
                f"{t.scope:<9} | {cats:<10} | "
                f"{t.counterparty}"
            )


    elif args.command == "scope-summary":
        txns = engine.all()
        summary = scope_wise_summary(txns)
        print_summary("Scope-wise Summary", summary)

    elif args.command == "edit":
        txns = engine.all()

        if args.id:
            txns = [t for t in txns if t.id.startswith(args.id)]

        if args.scope:
            txns = [t for t in txns if t.scope == args.scope]

        if args.category:
            txns = [t for t in txns if args.category in t.category]

        if not txns:
            print("✗ No matching transactions to edit.")
            return

        edited = edit_transactions(txns)
        if edited:
            store.update(edited)
            print(f"✓ Edited {len(edited)} transactions.")
        else:
            print("No transactions were edited.")

    elif args.command == "edit-tag":
        txns = engine.all()
        txns = [t for t in txns if t.id.startswith(args.id)]

        if not txns:
            print(f"✗ Transaction not found: {args.id}")
            return

        updated = edit_transaction_tag(txns[0])
        store.update([updated])
        print("✓ Tag updated.")


    else:
        parser.print_help()


if __name__ == "__main__":
    main()
