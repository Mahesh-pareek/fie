import pdfplumber
import re
from datetime import datetime
import os

PDF_PATH = "tests/canara1m.pdf"
DEBUG_DIR = "debug_dump"
DEBUG_FILE = os.path.join(DEBUG_DIR, "canara_all_rawtxns.txt")


COLS = {
    "DATE":        (20,  90),
    "PART":        (100, 300),
    "DEPOSIT":     (320, 395),
    "WITHDRAW":    (430, 495),
    "BALANCE":     (520, 590),
}

DATE_RE   = re.compile(r"\d{2}-\d{2}-\d{4}")
AMOUNT_RE = re.compile(r"[\d,]+\.\d{2}")

HEADER_WORDS = {
    "date", "particulars", "deposits", "withdrawals", "balance"
}

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

def is_header_word(txt):
    return txt.lower() in HEADER_WORDS

def is_footer_word(txt, column):
    # digits in PART column are VALID (chq id)
    return txt.lower() == "page" or (txt.isdigit() and column != "PART")

def is_chq_id(w):
    return w["text"].isdigit() and 6 <= len(w["text"]) <= 20

def run():
    state = "PRE_TABLE"
    seen_headers = set()

    opening_balance = None
    closing_balance = None

    current_txn = []
    txns = []
    waiting_for_chq_id = False

    print(f"\n[LOAD] {PDF_PATH}")
    print(f"[TIME] {datetime.now()}\n")

    with pdfplumber.open(PDF_PATH) as pdf:
        print(f"[INFO] Pages: {len(pdf.pages)}")

        for page_no, page in enumerate(pdf.pages, start=1):
            print(f"\n===== PAGE {page_no} =====")

            words = page.extract_words(
                use_text_flow=True,
                keep_blank_chars=False
            )
            words.sort(key=lambda w: w["top"])

            for w in words:
                txt = w["text"]
                y = round(w["top"], 1)
                column = col(w)

                # -------- FOOTER --------
                if is_footer_word(txt, column):
                    continue

                # -------- HEADER DETECTION --------
                if state == "PRE_TABLE":
                    if txt in {"Date","Particulars","Deposits","Withdrawals","Balance"}:
                        seen_headers.add(txt)
                        if len(seen_headers) == 5:
                            state = "WAIT_OPENING_BALANCE"
                            print(f"[STATE] PRE_TABLE → WAIT_OPENING_BALANCE @ y={y}")
                    continue

                # -------- HEADER IGNORE --------
                if is_header_word(txt):
                    continue

                # -------- OPENING BALANCE --------
                if state == "WAIT_OPENING_BALANCE":
                    if is_amount(w) and column == "BALANCE":
                        opening_balance = txt
                        state = "READY_FOR_TXN"
                        print(f"[GLOBAL] Opening Balance = {opening_balance}")
                    continue

                # -------- CLOSING BALANCE --------
                if txt == "Closing":
                    state = "POST_TABLE"
                    continue

                if state == "POST_TABLE":
                    if is_amount(w) and column == "BALANCE" and closing_balance is None:
                        closing_balance = txt
                        print(f"[GLOBAL] Closing Balance = {closing_balance}")
                    continue

                # -------- START TXN --------
                if state == "READY_FOR_TXN":
                    if txt == "Chq:":
                        continue
                    state = "IN_TXN"
                    current_txn = []
                    print(f"\n[TXN_START #{len(txns)+1}] page={page_no} y={y}")

                # -------- CHQ MARKER --------
                if state == "IN_TXN" and txt == "Chq:":
                    waiting_for_chq_id = True
                    continue

                # -------- CHQ ID (ENDS TXN) --------
                if state == "IN_TXN" and waiting_for_chq_id:
                    current_txn.append(w)

                    txns.append(list(current_txn))
                    summarize_txn(len(txns), current_txn)

                    current_txn.clear()
                    waiting_for_chq_id = False
                    state = "READY_FOR_TXN"
                    print(f"[TXN_END #{len(txns)}]")
                    continue

                # -------- NORMAL TXN WORD --------
                if state == "IN_TXN":
                    current_txn.append(w)

    print("\n========== FILE METRICS ==========")
    print(f"Opening Balance : {opening_balance}")
    print(f"Closing Balance : {closing_balance}")
    print(f"Transactions    : {len(txns)}")
    print("=================================")
import os



def summarize_txn(n, words):
    date = dep = wd = bal = chq = None
    parts = []

    for w in words:
        c = col(w)

        # ---- DATE ----
        if is_date(w) and not date:
            date = w["text"]

        # ---- AMOUNTS ----
        if is_amount(w):
            if c == "DEPOSIT":
                dep = w["text"]
            elif c == "WITHDRAW":
                wd = w["text"]
            elif c == "BALANCE":
                bal = w["text"]

        # ---- CHQ ID ----
        if chq is None and is_chq_id(w):
            chq = w["text"]

        # ---- PARTICULARS ----
        if c == "PART" and w["text"] != "Chq:":
            parts.append(w["text"])

    particulars = " ".join(parts)

    # ---- ensure debug dir exists ----
    os.makedirs(DEBUG_DIR, exist_ok=True)

    # ---- append to debug file ----
    with open(DEBUG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[TXN #{n}]\n")
        f.write(f"date        : {date}\n")
        f.write(f"type        : {'CR' if dep else 'DR'}\n")
        f.write(f"amount      : {dep or wd}\n")
        f.write(f"balance     : {bal}\n")
        f.write(f"chq_id      : {chq}\n")
        f.write(f"raw_txn     : {particulars}\n")
        f.write("-" * 50 + "\n")



if __name__ == "__main__":
    run()
