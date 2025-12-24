FIE — Frontend (minimal)

Quick start (using your `megatron` venv):

```bash
source ~/venvs/megratron/bin/activate
pip install -r requirements.txt
python -m flask --app fie.web_ui run --port 8080
```

Then open http://localhost:8080

Endpoints:
- `GET /api/transactions` — list transactions
- `GET /api/summary` — aggregates
- `POST /api/load` — upload PDF file (form field `file`)
- `POST /api/tag` — JSON body {id, scope, category}
- `GET /api/export.csv` — download CSV
