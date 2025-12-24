import pdfplumber
from pathlib import Path

PDF_DIR = Path("tests/")          # input PDFs
OUT_DIR = Path("debug_dump")   # output TXT files

OUT_DIR.mkdir(exist_ok=True)

def dump_pdf(pdf_path):
    out_file = OUT_DIR / f"{pdf_path.stem}_coords.txt"

    with pdfplumber.open(pdf_path) as pdf, open(out_file, "w", encoding="utf-8") as f:
        f.write(f"========== FILE: {pdf_path.name} ==========\n\n")

        for page_idx, page in enumerate(pdf.pages, start=1):
            f.write(f"\n======= PAGE {page_idx} =======\n\n")

            words = page.extract_words(
                use_text_flow=True,
                keep_blank_chars=False
            )
            
            words.sort(key=lambda w: w["top"])

            for w in words:
                line = (
                    f"text={w['text']!r:<40} "
                    f"x0={w['x0']:7.1f} "
                    f"x1={w['x1']:7.1f} "
                    f"top={w['top']:7.1f} "
                    f"bottom={w['bottom']:7.1f}\n"
                )
                f.write(line)

    print(f"✅ dumped: {out_file}")

def main():
    pdfs = sorted(PDF_DIR.glob("*.pdf"))

    if not pdfs:
        print("❌ No PDFs found in ./pdfs/")
        return

    for pdf in pdfs:
        dump_pdf(pdf)

if __name__ == "__main__":
    main()
