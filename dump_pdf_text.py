from pathlib import Path
import pdfplumber


TEST_DIR = Path("tests")   # your folder with PDFs
OUTPUT_DIR = Path("debug_dump")
OUTPUT_DIR.mkdir(exist_ok=True)


def dump_pdf(pdf_path: Path):
    out_file = OUTPUT_DIR / f"{pdf_path.stem}.txt"

    print(f"\n=== Dumping: {pdf_path.name} ===")

    with pdfplumber.open(pdf_path) as pdf, open(out_file, "w", encoding="utf-8") as f:
        for i, page in enumerate(pdf.pages, start=1):
            header = f"\n\n===== PAGE {i} =====\n"
            text = page.extract_text() or ""

            print(header)
            print(text)

            f.write(header)
            f.write(text)

    print(f"→ Saved raw text to {out_file}")


def main():
    pdfs = sorted(TEST_DIR.glob("*.pdf"))

    if not pdfs:
        print("No PDFs found in tests/")
        return

    for pdf in pdfs:
        dump_pdf(pdf)


if __name__ == "__main__":
    main()
