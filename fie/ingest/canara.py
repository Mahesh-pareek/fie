# fie/ingest/canara.py

import json
import re
from datetime import datetime, time
from pathlib import Path
import pdfplumber

from fie.core.transaction import Transaction


# ================= CONFIG =================

COLS = {
    "DATE":        (20,  90),
    "PART":        (100, 300),
    "DEPOSIT":     (320, 395),
    "WITHDRAW":    (430, 495),
    "BALANCE":     (520, 590),
}

DATE_RE   = re.compile(r"\d{2}-\d{2}-\d{4}")
TIME_RE   = re.compile(r"\b\d{2}:\d{2}:\d{2}\b")
AMOUNT_RE = re.compile(r"[\d,]+\.\d{2}")


# ================= BASIC HELPERS =================

def cx(w):
    return (w["x0"] + w["x1"]) / 2


def col(w):
    c = cx(w)
    for k, (l, r) in COLS.items():
        if l <= c <= r:
            return k
    return "OTHER"


def is_date(w):
    return DATE_RE.fullmatch(w["text"]) and col(w) == "DATE"


def is_amount(w):
    return AMOUNT_RE.fullmatch(w["text"])


def is_chq_id(w):
    return w["text"].isdigit() and 6 <= len(w["text"]) <= 20


def normalize_text(s: str) -> str:
    """
    Uppercase + collapse spaces
    """
    return " ".join(s.upper().replace("\n", " ").split())


def nospace_text(s: str) -> str:
    """
    Remove *all* spaces (for stable parsing)
    """
    return s.replace(" ", "")

def normalize_raw_spacing(s: str) -> str:
    """
    Remove spaces only between alphabetic tokens.
    Preserve spaces around numbers, dates, times.
    """
    tokens = s.split()

    out = []
    i = 0
    n = len(tokens)

    while i < n:
        cur = tokens[i]

        if cur.isalpha():
            j = i + 1
            merged = cur
            while j < n and tokens[j].isalpha():
                merged += tokens[j]
                j += 1
            out.append(merged)
            i = j
        else:
            out.append(cur)
            i += 1

    return " ".join(out)



# ================= SEMANTIC PARSING =================

def extract_time(raw: str) -> time | None:
    m = TIME_RE.search(raw)
    if not m:
        return None
    return datetime.strptime(m.group(), "%H:%M:%S").time()


def detect_mode(raw: str) -> str:
    r = raw.upper()
    if r.startswith("UPI/"):
        return "UPI"
    if "IMPS" in r:
        return "IMPS"
    if r.startswith("CASH DEPOSIT"):
        return "CASH"
    if "SETTLEMENT" in r:
        return "INTERNAL"
    return "UNKNOWN"


def parse_counterparty(raw: str, mode: str) -> str:
    parts = [p.strip() for p in raw.split("/") if p.strip()]

    name = "UNKNOWN"

    if mode == "UPI" and len(parts) >= 4:
        name = parts[3]

    elif mode == "IMPS" and len(parts) >= 2:
        name = parts[1]

    elif mode == "CASH" and len(parts) >= 2:
        name = parts[1]

    elif mode == "INTERNAL":
        name = parts[0]

    # cleanup: remove digits, collapse spaces
    name = re.sub(r"\d", "", name)
    name = " ".join(name.split())

    return name.upper() if name else "UNKNOWN"


# ================= TRANSACTION BUILDER =================

def build_transaction(words, source_file: str) -> Transaction | None:
    date = dep = wd = bal = chq = None
    parts = []

    for w in words:
        c = col(w)
        txt = w["text"]

        if is_date(w):
            date = txt

        if is_amount(w):
            if c == "DEPOSIT":
                dep = txt
            elif c == "WITHDRAW":
                wd = txt
            elif c == "BALANCE":
                bal = txt

        if chq is None and is_chq_id(w):
            chq = txt

        if c == "PART" and txt != "Chq:":
            parts.append(txt)

    if not date or not (dep or wd):
        return None

    raw_txn = normalize_text(" ".join(parts))
    raw_clean = normalize_raw_spacing(raw_txn)


    mode = detect_mode(raw_txn)
    counterparty = parse_counterparty(raw_txn, mode)
    direction = "credit" if dep else "debit"

    amount = float((dep or wd).replace(",", ""))
    balance = float(bal.replace(",", "")) if bal else None

    # ---- datetime with time ----
    txn_date = datetime.strptime(date, "%d-%m-%Y").date()
    txn_time = extract_time(raw_txn) or time(0, 0, 0)
    txn_dt = datetime.combine(txn_date, txn_time)

    txn_id = Transaction.compute_id(
        datetime=txn_dt,
        amount=amount,
        direction=direction,
        counterparty=counterparty,
        mode=mode,
        raw_txn=raw_txn,
        source_file=source_file,
    )

    extras = {
        "balance": balance,
        "chq_id": chq,
        "raw": raw_clean,
        "time": txn_time.isoformat(),
        "source_file": source_file,
    }

    return Transaction(
        id=txn_id,
        datetime=txn_dt,
        amount=amount,
        direction=direction,
        counterparty=counterparty,
        mode=mode,
        extras=extras,
    )


# ================= MAIN PARSER =================

def parse_canara_pdf(pdf_path: str) -> list[Transaction]:
    transactions: list[Transaction] = []

    with pdfplumber.open(pdf_path) as pdf:
        state = "PRE_TABLE"
        seen_headers = set()
        current_txn = []
        waiting_for_chq = False

        for page in pdf.pages:
            words = page.extract_words(use_text_flow=True)
            words.sort(key=lambda w: w["top"])

            for w in words:
                txt = w["text"]
                column = col(w)

                # footer
                if txt.lower() == "page":
                    continue
                if txt.isdigit() and column != "PART":
                    continue

                # header detection
                if state == "PRE_TABLE":
                    if txt in {"Date","Particulars","Deposits","Withdrawals","Balance"}:
                        seen_headers.add(txt)
                        if len(seen_headers) == 5:
                            state = "READY"
                    continue

                if txt.lower() in {"date","particulars","deposits","withdrawals","balance"}:
                    continue

                # start txn
                if state == "READY":
                    if txt == "Chq:":
                        continue
                    state = "IN_TXN"
                    current_txn = []

                # chq marker
                if state == "IN_TXN" and txt == "Chq:":
                    waiting_for_chq = True
                    continue

                # chq id → END TXN
                if state == "IN_TXN" and waiting_for_chq:
                    current_txn.append(w)

                    txn = build_transaction(current_txn, pdf_path)
                    if txn:
                        transactions.append(txn)

                    current_txn = []
                    waiting_for_chq = False
                    state = "READY"
                    continue

                if state == "IN_TXN":
                    current_txn.append(w)

    return transactions
