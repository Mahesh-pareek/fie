import argparse
from pathlib import Path

from fie.core.engine import FIEEngine
from fie.storage.json_store import JsonTransactionStore
from fie import config

from fie.app import list as list_cmd
from fie.app import load as load_cmd
from fie.app import summary as summary_cmd


DATA_PATH = Path(config.get("storage.data_path"))


def main():
    parser = argparse.ArgumentParser(
        prog="fie",
        description="FIE — Financial Intelligence Engine",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  fie ld canara.pdf
  fie ld statements/
  fie ls
  fie ls -a
  fie ls -s personal
  fie edit
  fie edit id:de223a7c
  fie sum

Tips:
- Use 'fie ls -a' for full transaction details
- Use 'fie edit' to tag and review transactions
- Use 'fie sum' to see category & scope summaries
"""
    )

    subparsers = parser.add_subparsers(dest="command")

    # -------- LOAD --------
    load = subparsers.add_parser(
        "load",
        aliases=["ld"],
        help="Load bank statement PDFs"
    )
    load.add_argument("path", help="PDF file or directory containing PDFs")

    # -------- LIST --------
    ls = subparsers.add_parser(
        "list",
        aliases=["ls"],
        help="List transactions",
        description="""
    List transactions with optional filters.

    Examples:
    fie ls
    fie ls -a
    fie ls -s personal
    fie ls -c coffee -n 10
    """,
        formatter_class=argparse.RawTextHelpFormatter
    )

    ls.add_argument(
        "-a", "--all",        action="store_true",
        help="Show full (exploded) transaction view"
    )

    ls.add_argument(
        "-s", "--scope",
        metavar="SCOPE",
        help="Filter by scope (personal, family, education, shared)"
    )

    ls.add_argument(
        "-c", "--category",
        metavar="CATEGORY",
        help="Filter by category (food, coffee, travel, etc.)"
    )

    ls.add_argument(
        "-d", "--direction",
        choices=["debit", "credit"],
        metavar="DIR",
        help="Filter by direction (debit | credit)"
    )

    ls.add_argument(
        "--sort",
        choices=["datetime", "amount", "scope", "counterparty"],
        default="datetime",
        metavar="FIELD",
        help="Sort by field (default: datetime)"
    )

    ls.add_argument(
        "-n", "--limit",
        type=int,
        metavar="N",
        help="Limit number of results"
    )

    # -------- EDIT --------
    edit = subparsers.add_parser(
        "edit",
        help="Review or edit transactions"
    )
    edit.add_argument("filter", nargs="?", help="id:<prefix> | scope:<scope>")

    # -------- SUMMARY --------
    summary = subparsers.add_parser(
        "summary",
        aliases=["sum"],
        help="Show spending summaries"
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    store = JsonTransactionStore(DATA_PATH)
    engine = FIEEngine(store)

    # ==================================================
    # COMMAND DISPATCH
    # ==================================================

    if args.command in ("load", "ld"):
        load_cmd.run(args, engine)

    elif args.command in ("list", "ls"):
        list_cmd.run(args, engine)

    elif args.command == "edit":
        edit_cmd.run(args, engine, store)

    elif args.command in ("summary", "sum"):
        summary_cmd.run(args, engine)


if __name__ == "__main__":
    main()
