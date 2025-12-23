import re
from datetime import datetime
from typing import List
import pdfplumber

from fie.core.transaction import Transaction


DATE_RE = re.compile(r"\b\d{2}-\d{2}-\d{4}\b")
MONEY_RE = re.compile(r"\b\d{1,3}(?:,\d{3})*\.\d{2}\b")
TIME_RE = re.compile(r"\b\d{2}:\d{2}:\d{2}\b")
CHQ_RE = re.compile(r"Chq:\s*(\d+)")

SKIP_PREFIXES = (
    "page ",
    "date particulars",
    "opening balance",
    "closing balance",
    "statement for",
    "disclaimer",
    "unless the constituent",
    "beware of phishing",
    "computer output",
)


def should_skip(line: str) -> bool:
    l = line.lower().strip()
    return not l or any(l.startswith(p) for p in SKIP_PREFIXES)


def normalize_narration(lines: list[str]) -> str:
    return " ".join(l.strip() for l in lines if l.strip())


# ------------------ protocol extraction ------------------

def extract_protocol_segment(narration: str) -> str | None:
    patterns = [
        r"(UPI/(?:DR|CR)/[^ ]+)",
        r"(MOB-IMPS-(?:DR|CR)/[^ ]+)",
        r"(CASH DEPOSIT[^ ]*(?: [^ ]*)*)",
        r"(IITDSETTLEMENT[^ ]+)",
    ]
    for pat in patterns:
        m = re.search(pat, narration, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def infer_mode_and_direction(narration: str) -> tuple[str, str]:
    proto = extract_protocol_segment(narration)
    if not proto:
        return "UNKNOWN", "debit"

    p = proto.upper()
    if p.startswith("UPI/DR"):
        return "UPI", "debit"
    if p.startswith("UPI/CR"):
        return "UPI", "credit"
    if p.startswith("MOB-IMPS-DR"):
        return "IMPS", "debit"
    if p.startswith("MOB-IMPS-CR"):
        return "IMPS", "credit"
    if p.startswith("CASH DEPOSIT"):
        return "CASH", "credit"
    if "SETTLEMENT" in p:
        return "SETTLEMENT", "credit"

    return "UNKNOWN", "debit"


def infer_counterparty(narration: str) -> str:
    proto = extract_protocol_segment(narration)
    if not proto:
        return "UNKNOWN"

    p = proto.strip()

    if p.startswith("CASH DEPOSIT"):
        return "SELF"
    if "SETTLEMENT" in p:
        return "IITD"

    parts = [x.strip() for x in p.split("/") if x.strip()]

    if parts and parts[0] == "UPI" and len(parts) >= 4:
        return parts[3].title()

    if parts and parts[0].startswith("MOB-IMPS") and len(parts) >= 2:
        return parts[1].title()

    return "UNKNOWN"


# ------------------ main parser ------------------

def parse_canara_pdf(path: str) -> List[Transaction]:
    lines: List[str] = []

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                lines.extend(l.strip() for l in text.splitlines())

    transactions: List[Transaction] = []

    current = {
        "raw": [],
        "money": [],
        "date": None,
        "time": None,
        "chq": None,
    }

    def finalize():
        if not current["date"] or len(current["money"]) < 2:
            return None

        amount = float(current["money"][-2].replace(",", ""))
        time_str = current["time"] or "00:00:00"

        dt = datetime.strptime(
            f"{current['date']} {time_str}",
            "%d-%m-%Y %H:%M:%S"
        )

        narration = normalize_narration(current["raw"])
        mode, direction = infer_mode_and_direction(narration)
        counterparty = infer_counterparty(narration).upper()

        txn_id = Transaction.compute_id(
            datetime=dt,
            amount=amount,
            direction=direction,
            counterparty=counterparty,
            mode=mode,
            reference=narration[:300],
            source_file=path,
        )

        return Transaction(
            id=txn_id,
            datetime=dt,
            amount=amount,
            direction=direction,
            counterparty=counterparty,
            mode=mode,
            reference=narration[:300],
            upi_id=current["chq"],
            source_file=path,
        )

    for line in lines:
        if should_skip(line):
            continue

        current["raw"].append(line)
        current["money"].extend(MONEY_RE.findall(line))

        d = DATE_RE.search(line)
        if d:
            current["date"] = d.group()

        t = TIME_RE.search(line)
        if t:
            current["time"] = t.group()

        chq = CHQ_RE.search(line)
        if chq:
            current["chq"] = chq.group(1)

            txn = finalize()
            if txn:
                transactions.append(txn)

            # reset AFTER Chq (true boundary)
            current = {
                "raw": [],
                "money": [],
                "date": None,
                "time": None,
                "chq": None,
            }

    return transactions
