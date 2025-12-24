# fie/app/load.py

from pathlib import Path
from fie.ingest.canara import parse_canara_pdf


def run(args, engine):
    p = Path(args.path)

    if p.is_file():
        pdfs = [p]
    elif p.is_dir():
        pdfs = list(p.glob("*.pdf"))
    else:
        print(f"✗ Invalid path: {p}")
        return

    if not pdfs:
        print("✗ No PDF files found.")
        return

    total = 0
    for pdf in pdfs:
        txns = parse_canara_pdf(str(pdf))
        engine.ingest(txns)
        total += len(txns)

    print(f"✓ Loaded {total} transactions from {len(pdfs)} file(s).")
