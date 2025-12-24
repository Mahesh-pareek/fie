from pathlib import Path
import subprocess

try:
    import pdfplumber
except ModuleNotFoundError:
    subprocess.check_call(["/home/jarvis/venvs/megatron/bin/pip", "install", "pdfplumber"]) 
    import pdfplumber

p = Path("Frontendplan.pdf")
if not p.exists():
    print("ERROR: Frontendplan.pdf not found in this directory:", p)
    raise SystemExit(1)

out = Path("debug_dump/Frontendplan.txt")
out.parent.mkdir(exist_ok=True)

with pdfplumber.open(p) as pdf, out.open('w', encoding='utf-8') as f:
    for i, page in enumerate(pdf.pages, 1):
        header = f"\n\n===== PAGE {i} =====\n"
        text = page.extract_text() or ""
        f.write(header)
        f.write(text)

print('WROTE', out)
