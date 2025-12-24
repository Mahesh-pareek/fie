# fie/app/list.py

def short_id(txn_id, n=8):
    return txn_id[:n]


def trunc(s, n=10):
    return s[:n] if len(s) > n else s


def signed_amount(txn):
    return txn.amount if txn.direction == "credit" else -txn.amount


def fmt_amount_fixed(amount, width=13):
    sign = "-" if amount < 0 else ""
    return f"{sign}{abs(amount):,.2f}₹".rjust(width)


def fmt_category(txn):
    return ",".join(txn.category) if txn.category else "-"


def fmt_bool(v):
    return "yes" if v else "no"


def run(args, engine):
    txns = engine.all()

    # ---------- filters ----------
    if args.scope:
        txns = [t for t in txns if t.scope == args.scope]
    if args.category:
        txns = [t for t in txns if args.category in t.category]
    if args.direction:
        txns = [t for t in txns if t.direction == args.direction]

    # ---------- sort & limit ----------
    txns.sort(key=lambda t: getattr(t, args.sort))
    if args.limit:
        txns = txns[:args.limit]

    if not txns:
        print("No transactions to display.")
        return

    # ==================================================
    # COMPACT VIEW (fie ls)
    # ==================================================
    if not args.all:
        print(
            f"{'#':<3} {'ID':<9} {'DATE':<12} {'AMOUNT':>10} "
            f"{'':>2}{'SCOPE':<9} {'CATEGORY':<9} COUNTERPARTY"
        )
        print("-" * 80)

        for i, t in enumerate(txns, 1):
            print(
                f"{i:<3} {short_id(t.id):<9} {t.datetime.date()} "
                f"{fmt_amount_fixed(signed_amount(t))} "
                f"{t.scope:<10} {fmt_category(t):<10} "
                f"{trunc(t.counterparty, 10)}"
            )

    # ==================================================
    # EXPLODED VIEW (fie ls -a)
    # ==================================================
    else:
        print(
            f"{'#':<3} {'ID':<9} {'DATE':<12} {'TIME':<9} "
            f"{'AMOUNT':>11}  {'DIR':<4} {'SCOPE':<9} "
            f"{'CATEGORY':<10} {'MODE':<8} {'REV':<4} COUNTERPARTY"
        )
        print("-" * 120)

        for i, t in enumerate(txns, 1):
            print(
                f"{i:<3} {short_id(t.id):<9} {t.datetime.date()} "
                f"{str(t.datetime.time()):<9} "
                f"{fmt_amount_fixed(signed_amount(t))}  "
                f"{('CR' if t.direction=='credit' else 'DR'):<4} "
                f"{t.scope:<10} {fmt_category(t):<10} "
                f"{t.mode:<8} {fmt_bool(t.reviewed):<4} "
                f"{t.counterparty}"
            )
