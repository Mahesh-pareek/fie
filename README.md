# FIE — Financial Intelligence Engine

A local-first personal finance tracker with CLI + Web UI.  
Turn bank statements into actionable financial insights.

## Features

### Core
- **PDF Ingestion** — Parse Canara Bank statements automatically
- **Smart Categorization** — Auto-tag transactions with configurable rules
- **Scope Management** — Separate personal, family, education, shared expenses
- **Budget Tracking** — Monthly budget with real-time monitoring

### Web Dashboard
- **Dashboard** — Money in/out, spending by category, trends
- **Transactions** — Full ledger with search, filter, bulk edit
- **Analytics** — Cross-scope comparison, top merchants, patterns
- **Auto-Tagging** — Rule builder with preview and manual edit protection
- **Activity Log** — Track all changes with soft delete/restore
- **Help** — Built-in documentation with formulas explained

## Quick Start

```bash
# Install
pip install -e .

# Start web UI
python fie/web_ui.py
# → http://localhost:8080 (default: admin/admin)

# CLI commands
fie ls                    # List transactions
fie summary               # Show summary
fie edit                  # Interactive tagging
```

## Stack
- **Backend:** Flask + JSON storage
- **Frontend:** Vanilla JS + Chart.js
- **Parser:** pdfplumber for PDF extraction

## Project Structure
```
fie/
├── web_ui.py          # Flask server + API
├── defaults.py        # Configurable defaults
├── core/              # Engine, rules, transaction model
├── ingest/            # PDF parsers
├── storage/           # JSON persistence
├── static/            # CSS + JS
└── templates/         # HTML
```

## Configuration

Settings stored in `~/.config/fie/`:
- `settings.json` — Budget, scopes, categories
- `auto_rules.json` — Auto-tagging rules
- `activity_logs.json` — Change history
- `trash.json` — Soft-deleted transactions

## License
MIT
