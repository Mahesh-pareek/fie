# 💰 FIE — Financial Intelligence Engine

A privacy-first personal finance tracker with automatic transaction categorization. Import your bank statements, let FIE auto-tag transactions, and gain insights into your spending habits.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-green.svg)
![Flask](https://img.shields.io/badge/flask-3.0+-orange.svg)

## ✨ Features

### 📊 Dashboard
- **At-a-glance overview** — Total spending, transaction count, top categories
- **Interactive charts** — Spending trends and category breakdowns with Chart.js
- **Period comparison** — Month, quarter, year views with comparison to previous period
- **Recent transactions** — Quick view of latest activity

### 📋 Transaction Management
- **Smart filtering** — Filter by scope, category, direction, search text
- **Bulk operations** — Select multiple transactions for batch tagging or deletion
- **Keyboard navigation** — Power-user shortcuts (j/k, e, d, etc.)
- **Pagination** — Load more transactions on demand
- **Notes support** — Add personal notes to any transaction
- **Soft delete** — Undo accidental deletions within 5 seconds

### 🤖 Auto-Tagging Rules
- **Merchant-based rules** — Auto-categorize by merchant name
- **Amount-based rules** — Tag transactions by amount range
- **Combined rules** — Match on multiple conditions
- **Rule preview** — See which transactions will be affected before applying
- **Quick rule creation** — Create rules directly from transactions with ⚡ button

### 📈 Analytics
- **Scope breakdown** — Personal, Family, Education, Shared spending
- **Category insights** — Top spending categories with percentages
- **Trend analysis** — Daily/weekly/monthly spending patterns
- **Merchant analysis** — Top merchants and spending frequency

### 🔧 Additional Features
- **PDF import** — Supports Canara Bank statements (extensible)
- **CSV export** — Export filtered transactions
- **Manual transactions** — Add transactions manually
- **Activity logs** — Track all changes with audit trail
- **Recurring detection** — Identify recurring payments

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/fie.git
cd fie

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Or install from requirements
pip install -r requirements.txt
```

### Running the Web UI

```bash
# Start the web server
python -m fie web --port 8080

# Or using Flask directly
flask --app fie.web_ui run --port 8080
```

Then open http://localhost:8080

**Default login:** `admin` / `admin` (change in production!)

### Using the CLI

```bash
# Load bank statements
fie load /path/to/statement.pdf

# List transactions
fie list --scope personal --limit 20

# Show summary
fie summary

# Interactive edit mode
fie edit
```

## 📁 Project Structure

```
fie/
├── fie/
│   ├── web_ui.py        # Flask web application
│   ├── cli.py           # Command-line interface
│   ├── core/
│   │   ├── engine.py    # Transaction engine
│   │   ├── rules.py     # Auto-tagging rules
│   │   └── transaction.py
│   ├── ingest/
│   │   └── canara.py    # Bank statement parser
│   ├── storage/
│   │   └── json_store.py
│   ├── static/
│   │   ├── app.js       # Frontend application
│   │   └── styles.css
│   └── templates/
│       └── index.html
├── tests/
├── pyproject.toml
└── README.md
```

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `j` / `k` | Navigate up/down in transaction list |
| `e` | Edit selected transaction |
| `d` | Delete selected transaction |
| `x` | Toggle selection |
| `/` | Focus search |
| `n` | New transaction |
| `Esc` | Close modal / Clear selection |
| `?` | Show shortcuts help |
| `1-5` | Switch views (Dashboard, Transactions, etc.) |

## 🔌 API Reference

### Transactions
- `GET /api/transactions` — List transactions (supports `limit`, `offset`, `scope`, `category`, `direction`, `search`, `sort`, `order`)
- `POST /api/transactions` — Create manual transaction
- `PUT /api/transactions/<id>` — Update transaction
- `DELETE /api/transactions/<id>` — Soft delete transaction

### Summary & Analytics
- `GET /api/summary` — Aggregated spending summary
- `GET /api/health` — Dashboard health metrics
- `GET /api/trends` — Spending trends over time

### Auto-Tagging
- `GET /api/rules` — List all rules
- `POST /api/rules` — Create new rule
- `PUT /api/rules/<id>` — Update rule
- `DELETE /api/rules/<id>` — Delete rule
- `POST /api/rules/apply` — Apply rules to transactions
- `POST /api/rules/preview` — Preview rule effects

### Import/Export
- `POST /api/load` — Upload PDF statement (multipart form)
- `GET /api/export.csv` — Download transactions as CSV

## 🛠️ Configuration

Settings are stored in `fie/settings.json`:

```json
{
  "scopes": ["personal", "family", "education", "shared", "ignore"],
  "categories": ["food", "travel", "shopping", "bills", ...],
  "thresholds": {
    "large_transaction": 5000
  }
}
```

Auto-tagging rules are in `fie/auto_rules.json`.

## 🔒 Privacy & Security

- **Local-first** — All data stored locally, no cloud sync
- **No tracking** — Zero analytics or telemetry
- **Session auth** — Simple password protection for web UI
- **Your data stays yours** — Export anytime, delete anytime

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Flask](https://flask.palletsprojects.com/)
- Charts by [Chart.js](https://www.chartjs.org/)
- PDF parsing by [pdfplumber](https://github.com/jsvine/pdfplumber)

---

<p align="center">Made with ❤️ for better financial awareness</p>
