import re
from datetime import datetime
from typing import List
import pdfplumber

from fie.core.transaction import Transaction


DATE_LINE_RE = re.compile(r"(\d{2}-\d{2}-\d{4})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})")
TIME_RE = re.compile(r"\d{2}:\d{2}:\d{2}")


def parse_canara_pdf(path: str) -> List[Transaction]:
    transactions: List[Transaction] = []

    with pdfplumber.open(path) as pdf:
        lines: List[str] = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                lines.extend([l.strip() for l in text.splitlines()])

    i = 0
    while i < len(lines):
        line = lines[i]

        # Transaction header
        if "UPI/DR" in line or "UPI/CR" in line:
            direction = "debit" if "UPI/DR" in line else "credit"
            header_lines = [line]
            i += 1

            # Collect until date line
            while i < len(lines) and not DATE_LINE_RE.search(lines[i]):
                header_lines.append(lines[i])
                i += 1

            if i >= len(lines):
                break

            # Date + amount line
            date_line = lines[i]
            m = DATE_LINE_RE.search(date_line)
            if not m:
                i += 1
                continue

            date_str, amount_str, _balance = m.groups()
            amount = float(amount_str.replace(",", ""))

            # Look ahead for time
            time_str = "00:00:00"
            if i + 1 < len(lines) and TIME_RE.search(lines[i + 1]):
                time_str = TIME_RE.search(lines[i + 1]).group()

            dt = datetime.strptime(
                f"{date_str} {time_str}",
                "%d-%m-%Y %H:%M:%S"
            )

            # Counterparty heuristic
            parts = header_lines[0].split("/")
            counterparty = parts[3] if len(parts) > 3 else "UNKNOWN"

            txn_id = Transaction.compute_id(
                datetime=dt,
                amount=amount,
                direction=direction,
                counterparty=counterparty,
                reference=" ".join(header_lines)[:80],
                source_file=path,
            )

            transactions.append(
                Transaction(
                    id=txn_id,
                    datetime=dt,
                    amount=amount,
                    direction=direction,
                    counterparty=counterparty,
                    reference=" ".join(header_lines)[:120],
                    upi_id=None,
                    source_file=path,
                )
            )

        i += 1

    return transactions
