from pathlib import Path
import tempfile
import os
import functools
from datetime import datetime
from flask import Flask, render_template, jsonify, request, session, redirect, url_for

from fie.core.engine import FIEEngine
from fie.storage.json_store import JsonTransactionStore
from fie import config
from fie.defaults import (
    get_default_rules, get_default_settings,
    get_split_categories, DEFAULT_CATEGORIES, DEFAULT_SCOPES
)
from fie.ingest.canara import parse_canara_pdf
from fie.core.transaction import Transaction

DATA_PATH = Path(config.get("storage.data_path"))
store = JsonTransactionStore(DATA_PATH)
engine = FIEEngine(store)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "fie-secret-key-change-in-prod"

# Simple hardcoded credentials (replace with DB in production)
USERS = {
    "admin": "password"
}


def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "Unauthorized"}), 401
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated


def txn_to_dict(t):
    return {
        "id": t.id,
        "datetime": t.datetime.isoformat(),
        "amount": t.amount,
        "direction": t.direction,
        "scope": t.scope,
        "category": t.category,
        "counterparty": t.counterparty,
        "mode": t.mode,
        "reviewed": t.reviewed,
    }


@app.route("/login")
def login_page():
    if session.get("logged_in"):
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    username = data.get("username", "")
    password = data.get("password", "")
    
    if username in USERS and USERS[username] == password:
        session["logged_in"] = True
        session["username"] = username
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Invalid credentials"}), 401


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/api/transactions")
@login_required
def api_transactions():
    args = request.args
    txns = engine.all()

    # filters
    scope = args.get("scope")
    if scope:
        txns = [t for t in txns if t.scope == scope]
    category = args.get("category")
    if category:
        txns = [t for t in txns if category in t.category]
    direction = args.get("direction")
    if direction:
        txns = [t for t in txns if t.direction == direction]
    
    # search filter
    search = args.get("search", "").lower()
    if search:
        txns = [t for t in txns if search in t.counterparty.lower() or search in str(t.amount)]

    sort = args.get("sort", "datetime")
    reverse = args.get("order", "desc") == "desc"
    txns.sort(key=lambda t: getattr(t, sort), reverse=reverse)

    limit = args.get("limit")
    if limit:
        try:
            limit = int(limit)
            txns = txns[:limit]
        except ValueError:
            pass

    data = [txn_to_dict(t) for t in txns]
    return jsonify(data)


@app.route("/api/summary")
@login_required
def api_summary():
    """Summary with optional scope filter. Default: personal only for dashboard."""
    scope_filter = request.args.get("scope", "personal")  # Default to personal
    txns = engine.all()
    
    # Filter by scope if specified (use "all" for no filter)
    if scope_filter != "all":
        txns = [t for t in txns if t.scope == scope_filter]

    # category aggregation
    cat_counts = {}
    cat_totals = {}  # Net totals (credits - debits)
    spending_by_cat = {}  # Only spending (debits)
    income_by_cat = {}  # Only income (credits)
    
    # Credits breakdown: splits vs deposits (use configurable categories)
    splits_total = 0.0  # Friend paybacks, refunds - shouldn't count as income
    deposits_total = 0.0  # True income (parents, salary, etc.)
    splits_categories = get_split_categories()  # From defaults.py
    
    for t in txns:
        key = t.category[0] if t.category else "unknown"
        cat_counts[key] = cat_counts.get(key, 0) + 1
        amt = t.amount if t.direction == "credit" else -t.amount
        cat_totals[key] = cat_totals.get(key, 0.0) + amt
        
        # Separate spending vs income
        if t.direction == "debit":
            spending_by_cat[key] = spending_by_cat.get(key, 0.0) + t.amount
        else:
            income_by_cat[key] = income_by_cat.get(key, 0.0) + t.amount
            # Classify credits: splits vs deposits
            is_split = any(cat in splits_categories for cat in (t.category or []))
            if is_split:
                splits_total += t.amount
            else:
                deposits_total += t.amount

    # scope aggregation (for all scopes view)
    all_txns = engine.all()
    scopes = config.get("tagging.scope_map").values()
    scope_counts = {s: 0 for s in scopes}
    scope_totals = {s: 0.0 for s in scopes}
    for t in all_txns:
        key = t.scope
        amt = t.amount if t.direction == "credit" else -t.amount
        scope_counts[key] = scope_counts.get(key, 0) + 1
        scope_totals[key] = scope_totals.get(key, 0.0) + amt

    return jsonify({
        "total_transactions": len(txns),
        "scope_filter": scope_filter,
        "by_category": {"counts": cat_counts, "totals": cat_totals},
        "spending_by_category": spending_by_cat,  # Only debits for spending chart
        "income_by_category": income_by_cat,  # Only credits
        "credits_breakdown": {
            "splits": splits_total,  # Friend paybacks (offset spending)
            "deposits": deposits_total,  # True income
        },
        "by_scope": {"counts": scope_counts, "totals": scope_totals},
    })


@app.route("/api/trends")
@login_required
def api_trends():
    """Return monthly and weekly spending trends with optional scope filter."""
    from collections import defaultdict
    scope_filter = request.args.get("scope", "personal")  # Default to personal
    start_date = request.args.get("start")  # YYYY-MM-DD
    end_date = request.args.get("end")  # YYYY-MM-DD
    
    txns = engine.all()
    
    # Filter by scope
    if scope_filter != "all":
        txns = [t for t in txns if t.scope == scope_filter]
    
    # Filter by date range if provided
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            txns = [t for t in txns if t.datetime >= start_dt]
        except:
            pass
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            txns = [t for t in txns if t.datetime <= end_dt]
        except:
            pass
    
    monthly = defaultdict(float)
    weekly = defaultdict(float)
    daily = defaultdict(float)
    
    # Daily by category (for personal expenses chart)
    daily_by_cat = defaultdict(lambda: defaultdict(float))
    
    # Running totals for cumulative line chart
    daily_cumulative = defaultdict(float)
    running_total = 0
    
    # Sort transactions by date for cumulative calculation
    sorted_txns = sorted(txns, key=lambda t: t.datetime)
    
    for t in sorted_txns:
        amt = t.amount if t.direction == "credit" else -t.amount
        month_key = t.datetime.strftime("%Y-%m")
        monthly[month_key] += amt
        
        # ISO week
        week_key = t.datetime.strftime("%Y-W%W")
        weekly[week_key] += amt
        
        # Daily
        day_key = t.datetime.strftime("%Y-%m-%d")
        daily[day_key] += amt
        
        # Daily by category
        cat = t.category[0] if t.category else "unknown"
        if t.direction == "debit":
            daily_by_cat[day_key][cat] += t.amount
        
        # Cumulative (spending only)
        if t.direction == "debit":
            running_total += t.amount
            daily_cumulative[day_key] = running_total
    
    # Get all daily data, limited to last 90 days if no date filter
    all_daily = dict(sorted(daily.items()))
    all_daily_by_cat = {k: dict(v) for k, v in sorted(daily_by_cat.items())}
    all_cumulative = dict(sorted(daily_cumulative.items()))
    
    # If no date filter, limit to last 30 days for display
    if not start_date and not end_date:
        display_daily = dict(list(sorted(daily.items()))[-30:])
        display_daily_by_cat = {k: dict(v) for k, v in list(sorted(daily_by_cat.items()))[-30:]}
        display_cumulative = dict(list(sorted(daily_cumulative.items()))[-30:])
    else:
        display_daily = all_daily
        display_daily_by_cat = all_daily_by_cat
        display_cumulative = all_cumulative
    
    # Get date range info
    all_dates = list(all_daily.keys())
    
    return jsonify({
        "monthly": dict(sorted(monthly.items())),
        "weekly": dict(sorted(weekly.items())[-12:]),
        "daily": display_daily,
        "daily_by_category": display_daily_by_cat,
        "daily_cumulative": display_cumulative,
        "date_range": {
            "min": all_dates[0] if all_dates else None,
            "max": all_dates[-1] if all_dates else None,
            "total_days": len(all_dates),
            "filtered": bool(start_date or end_date)
        }
    })


@app.route("/api/analytics")
@login_required
def api_analytics():
    """Comprehensive analytics for all scopes - optimized single pass."""
    from collections import defaultdict
    
    txns = engine.all()
    settings = load_settings()
    all_scopes = settings.get("scopes", ["personal", "family", "education", "shared"])
    
    now = datetime.now()
    this_month = now.month
    this_year = now.year
    
    # Initialize data structures for single-pass processing
    scope_data = {s: {
        "count": 0, "spent": 0.0, "income": 0.0, "this_month": 0.0,
        "categories": defaultdict(float),
        "merchants": defaultdict(float),
        "monthly": defaultdict(float),
        "weekly": defaultdict(float),
    } for s in all_scopes}
    
    comparison_monthly = defaultdict(lambda: {s: 0.0 for s in all_scopes})
    scope_totals = {s: 0.0 for s in all_scopes}
    
    # Single pass over all transactions
    for t in txns:
        scope = t.scope
        if scope not in scope_data:
            continue
        
        sd = scope_data[scope]
        sd["count"] += 1
        
        is_debit = t.direction == "debit"
        if is_debit:
            sd["spent"] += t.amount
            scope_totals[scope] += t.amount
            
            # Category
            cat = t.category[0] if t.category else "unknown"
            sd["categories"][cat] += t.amount
            
            # Merchant
            sd["merchants"][t.counterparty] += t.amount
            
            # Monthly/weekly trends
            month_key = t.datetime.strftime("%Y-%m")
            sd["monthly"][month_key] += t.amount
            sd["weekly"][t.datetime.strftime("%Y-W%W")] += t.amount
            
            # Comparison monthly
            comparison_monthly[month_key][scope] += t.amount
            
            # This month
            if t.datetime.year == this_year and t.datetime.month == this_month:
                sd["this_month"] += t.amount
        else:
            sd["income"] += t.amount
    
    # Build result
    result = {"scopes": {}, "comparison": {}}
    
    for scope in all_scopes:
        sd = scope_data[scope]
        top_merchants = sorted(sd["merchants"].items(), key=lambda x: -x[1])[:5]
        
        result["scopes"][scope] = {
            "total_transactions": sd["count"],
            "total_spent": sd["spent"],
            "total_income": sd["income"],
            "this_month_spent": sd["this_month"],
            "categories": dict(sd["categories"]),
            "top_merchants": [{"name": m, "amount": a} for m, a in top_merchants],
            "monthly": dict(sorted(sd["monthly"].items())[-6:]),
            "weekly": dict(sorted(sd["weekly"].items())[-8:]),
        }
    
    result["comparison"]["monthly"] = dict(sorted(comparison_monthly.items())[-6:])
    result["comparison"]["totals"] = scope_totals
    
    return jsonify(result)


@app.route('/api/meta')
@login_required
def api_meta():
    """Return tagging maps for UI (scopes, categories)."""
    try:
        tagging = config.get('tagging')
        scope_map = tagging.get('scope_map', {})
        category_map = tagging.get('category_map', {})
    except Exception:
        scope_map = {}
        category_map = {}

    return jsonify({
        'scopes': list(scope_map.values()),
        'categories': list(category_map.values()),
    })


@app.route("/api/load", methods=["POST"])
@login_required
def api_load():
    # Accept either an uploaded file (form field 'file') or a path (form field 'path')
    if "file" in request.files:
        f = request.files["file"]
        if f.filename == "":
            return jsonify({"error": "No file provided"}), 400
        tmpdir = Path(tempfile.mkdtemp(prefix="fie_upload_"))
        save_path = tmpdir / f.filename
        f.save(save_path)
        pdf_path = str(save_path)
        filename = f.filename
    else:
        pdf_path = request.form.get("path")
        if not pdf_path:
            return jsonify({"error": "No file or path provided"}), 400
        filename = Path(pdf_path).name

    # parse and ingest
    try:
        txns = parse_canara_pdf(pdf_path)
        engine.ingest(txns)
        count = len(txns)
        
        # Auto-tag new transactions
        tagged_count = auto_tag_new_transactions()
        
        # Log the upload
        save_log("upload", {"filename": filename, "transactions_added": count, "auto_tagged": tagged_count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"ok": True, "count": count, "auto_tagged": tagged_count})


def auto_tag_new_transactions():
    """Apply auto-tagging rules to unreviewed transactions."""
    from dataclasses import replace as dc_replace
    
    rules = load_rules()
    rules = sorted([r for r in rules if r.get("enabled", True)], key=lambda r: r.get("priority", 999))
    
    txns = engine.all()
    updated = []
    
    for txn in txns:
        # Only tag unreviewed transactions
        if txn.reviewed:
            continue
        
        # Try each rule in priority order
        for rule in rules:
            if match_rule(txn, rule):
                new_txn = apply_rule(txn, rule)
                if new_txn != txn:
                    updated.append(new_txn)
                break  # First matching rule wins
    
    # Save updated transactions
    if updated:
        store.update(updated)
    
    return len(updated)


@app.route("/api/tag", methods=["POST"])
@login_required
def api_tag():
    """Update tags/scope for a transaction.
    Expects JSON: {"id": "...", "scope": "personal", "category": ["food"]}
    """
    from dataclasses import replace

    data = request.get_json() or {}
    tid = data.get("id")
    if not tid:
        return jsonify({"error": "id required"}), 400

    # find txn
    txns = engine.all()
    match = [t for t in txns if t.id == tid]
    if not match:
        return jsonify({"error": "transaction not found"}), 404

    t = match[0]
    updates = {}
    old_values = {}
    if "scope" in data and data["scope"] != t.scope:
        old_values["scope"] = t.scope
        updates["scope"] = data["scope"]
    if "category" in data:
        old_values["category"] = t.category
        updates["category"] = data["category"]

    if updates:
        updates["reviewed"] = True
        new_t = replace(t, **updates)
        try:
            store.update([new_t])
            # Log the edit
            save_log("edit", {
                "transaction_id": tid,
                "counterparty": t.counterparty,
                "old": old_values,
                "new": {k: v for k, v in updates.items() if k != "reviewed"}
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return jsonify({"ok": True, "changed": bool(updates)})


@app.route("/api/export.csv")
@login_required
def api_export_csv():
    import io
    import csv

    txns = engine.all()

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "datetime", "amount", "direction", "scope", "category", "counterparty"])
    for t in txns:
        w.writerow([t.id, t.datetime.isoformat(), t.amount, t.direction, t.scope, ",".join(t.category), t.counterparty])

    resp = app.response_class(buf.getvalue(), mimetype="text/csv")
    resp.headers["Content-Disposition"] = "attachment; filename=transactions.csv"
    return resp


# ============ SETTINGS ============

SETTINGS_FILE = DATA_PATH.parent / "settings.json"
RULES_FILE = DATA_PATH.parent / "auto_rules.json"


def load_settings():
    """Load user settings, falling back to defaults."""
    import json
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE) as f:
                user_settings = json.load(f)
                # Merge with defaults to ensure all keys exist
                defaults = get_default_settings()
                defaults.update(user_settings)
                return defaults
        except:
            pass
    return get_default_settings()


# ============ AUTO-TAGGING RULES ============

def load_rules():
    """Load auto-tagging rules from file, falling back to defaults."""
    import json
    if RULES_FILE.exists():
        try:
            with open(RULES_FILE) as f:
                return json.load(f)
        except:
            pass
    # Return defaults from defaults.py
    return get_default_rules()


def save_rules(rules):
    """Save auto-tagging rules to file."""
    import json
    RULES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RULES_FILE, 'w') as f:
        json.dump(rules, f, indent=2)


def match_rule(txn, rule):
    """Check if a transaction matches a rule's conditions."""
    if not rule.get("enabled", True):
        return False
    
    conditions = rule.get("conditions", {})
    rule_type = rule.get("type", "amount")
    
    # Amount conditions
    if rule_type in ["amount", "combined"]:
        amount_min = conditions.get("amount_min")
        amount_max = conditions.get("amount_max")
        if amount_min is not None and txn.amount < amount_min:
            return False
        if amount_max is not None and txn.amount > amount_max:
            return False
    
    # Merchant/counterparty conditions (supports comma-separated multiple values)
    if rule_type in ["merchant", "combined"]:
        merchant_contains = conditions.get("merchant_contains", "").lower()
        merchant_exact = conditions.get("merchant_exact", "").lower()
        counterparty = txn.counterparty.lower()
        
        # Check exact match (supports comma-separated: match ANY)
        if merchant_exact:
            exact_matches = [m.strip() for m in merchant_exact.split(",") if m.strip()]
            if not any(counterparty == m for m in exact_matches):
                return False
        
        # Check contains match (supports comma-separated: match ANY)
        if merchant_contains:
            contains_keywords = [m.strip() for m in merchant_contains.split(",") if m.strip()]
            if not any(kw in counterparty for kw in contains_keywords):
                return False
    
    # Direction condition (optional)
    if "direction" in conditions:
        if txn.direction != conditions["direction"]:
            return False
    
    return True


def apply_rule(txn, rule):
    """Apply a rule's actions to a transaction."""
    from dataclasses import replace
    
    actions = rule.get("actions", {})
    updates = {}
    
    if "scope" in actions:
        updates["scope"] = actions["scope"]
    if "category" in actions:
        updates["category"] = actions["category"]
    
    updates["reviewed"] = True
    return replace(txn, **updates)


@app.route("/api/rules", methods=["GET"])
@login_required
def api_get_rules():
    """Get all auto-tagging rules."""
    return jsonify(load_rules())


@app.route("/api/rules", methods=["POST"])
@login_required
def api_add_rule():
    """Add a new auto-tagging rule."""
    import uuid
    data = request.get_json() or {}
    
    rules = load_rules()
    
    new_rule = {
        "id": f"rule_{uuid.uuid4().hex[:8]}",
        "name": data.get("name", "New Rule"),
        "type": data.get("type", "amount"),  # amount, merchant, combined
        "enabled": data.get("enabled", True),
        "priority": data.get("priority", len(rules) + 1),
        "conditions": data.get("conditions", {}),
        "actions": data.get("actions", {}),
    }
    
    rules.append(new_rule)
    save_rules(rules)
    
    return jsonify({"ok": True, "rule": new_rule})


@app.route("/api/rules/<rule_id>", methods=["PUT"])
@login_required
def api_update_rule(rule_id):
    """Update an existing rule."""
    data = request.get_json() or {}
    rules = load_rules()
    
    for i, rule in enumerate(rules):
        if rule["id"] == rule_id:
            # Update allowed fields
            if "name" in data:
                rules[i]["name"] = data["name"]
            if "type" in data:
                rules[i]["type"] = data["type"]
            if "enabled" in data:
                rules[i]["enabled"] = data["enabled"]
            if "priority" in data:
                rules[i]["priority"] = data["priority"]
            if "conditions" in data:
                rules[i]["conditions"] = data["conditions"]
            if "actions" in data:
                rules[i]["actions"] = data["actions"]
            
            save_rules(rules)
            return jsonify({"ok": True, "rule": rules[i]})
    
    return jsonify({"error": "Rule not found"}), 404


@app.route("/api/rules/<rule_id>", methods=["DELETE"])
@login_required
def api_delete_rule(rule_id):
    """Delete a rule."""
    rules = load_rules()
    rules = [r for r in rules if r["id"] != rule_id]
    save_rules(rules)
    return jsonify({"ok": True})


@app.route("/api/rules/defaults", methods=["GET"])
@login_required
def api_get_default_rules():
    """Get the default rules (for reference/reset)."""
    return jsonify(get_default_rules())


@app.route("/api/rules/reset", methods=["POST"])
@login_required
def api_reset_rules():
    """Reset rules to defaults."""
    data = request.get_json() or {}
    mode = data.get("mode", "replace")  # "replace" or "merge"
    
    default_rules = get_default_rules()
    
    if mode == "merge":
        # Merge: Add defaults that don't exist
        current_rules = load_rules()
        current_ids = {r["id"] for r in current_rules}
        for default in default_rules:
            if default["id"] not in current_ids:
                current_rules.append(default)
        # Re-sort by priority
        current_rules.sort(key=lambda r: r.get("priority", 999))
        save_rules(current_rules)
        return jsonify({"ok": True, "mode": "merge", "count": len(current_rules)})
    else:
        # Replace: Full reset to defaults
        save_rules(default_rules)
        return jsonify({"ok": True, "mode": "replace", "count": len(default_rules)})


@app.route("/api/rules/reorder", methods=["POST"])
@login_required
def api_reorder_rules():
    """Reorder rules by priority."""
    data = request.get_json() or {}
    order = data.get("order", [])  # List of rule IDs in desired order
    
    rules = load_rules()
    rules_by_id = {r["id"]: r for r in rules}
    
    # Reorder based on provided order
    new_rules = []
    for i, rule_id in enumerate(order):
        if rule_id in rules_by_id:
            rule = rules_by_id[rule_id]
            rule["priority"] = i + 1
            new_rules.append(rule)
            del rules_by_id[rule_id]
    
    # Add any remaining rules not in the order
    for rule in rules_by_id.values():
        rule["priority"] = len(new_rules) + 1
        new_rules.append(rule)
    
    save_rules(new_rules)
    return jsonify({"ok": True})


@app.route("/api/rules/apply", methods=["POST"])
@login_required
def api_apply_rules():
    """Apply all rules to existing transactions (recompute)."""
    data = request.get_json() or {}
    only_unreviewed = data.get("only_unreviewed", False)
    
    rules = load_rules()
    rules = sorted([r for r in rules if r.get("enabled", True)], key=lambda r: r.get("priority", 999))
    
    txns = engine.all()
    updated = []
    
    for txn in txns:
        # Skip already reviewed if only_unreviewed is True
        if only_unreviewed and txn.reviewed:
            continue
        
        # Try each rule in priority order
        for rule in rules:
            if match_rule(txn, rule):
                new_txn = apply_rule(txn, rule)
                if new_txn != txn:
                    updated.append(new_txn)
                break  # First matching rule wins
    
    # Save updated transactions
    if updated:
        store.update(updated)
    
    # Log the auto-tag action
    save_log("auto_tag", {"updated": len(updated), "total": len(txns), "only_unreviewed": only_unreviewed})
    
    return jsonify({"ok": True, "updated": len(updated), "total": len(txns)})


@app.route("/api/rules/preview", methods=["POST"])
@login_required
def api_preview_rules():
    """Preview what rules would apply to transactions without saving."""
    data = request.get_json() or {}
    only_unreviewed = data.get("only_unreviewed", False)
    
    rules = load_rules()
    rules = sorted([r for r in rules if r.get("enabled", True)], key=lambda r: r.get("priority", 999))
    
    txns = engine.all()
    preview = []
    
    for txn in txns:
        if only_unreviewed and txn.reviewed:
            continue
        
        for rule in rules:
            if match_rule(txn, rule):
                preview.append({
                    "id": txn.id,
                    "counterparty": txn.counterparty,
                    "amount": txn.amount,
                    "current_scope": txn.scope,
                    "current_category": txn.category,
                    "new_scope": rule["actions"].get("scope", txn.scope),
                    "new_category": rule["actions"].get("category", txn.category),
                    "rule_name": rule["name"],
                })
                break
    
    return jsonify({"matches": preview, "count": len(preview)})


@app.route("/api/merchants")
@login_required
def api_get_merchants():
    """Get list of unique merchants/counterparties for autocomplete."""
    txns = engine.all()
    merchants = {}
    for t in txns:
        cp = t.counterparty
        if cp not in merchants:
            merchants[cp] = {"count": 0, "total": 0.0}
        merchants[cp]["count"] += 1
        if t.direction == "debit":
            merchants[cp]["total"] += t.amount
    
    # Sort by count
    result = [{"name": k, "count": v["count"], "total": v["total"]} 
              for k, v in sorted(merchants.items(), key=lambda x: -x[1]["count"])]
    
    return jsonify(result[:100])  # Top 100


def save_settings(settings):
    import json
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)


@app.route("/api/settings", methods=["GET"])
@login_required
def api_get_settings():
    return jsonify(load_settings())


@app.route("/api/settings", methods=["POST"])
@login_required
def api_save_settings():
    data = request.get_json() or {}
    settings = load_settings()
    
    # Update allowed fields
    if "monthly_budget" in data:
        settings["monthly_budget"] = float(data["monthly_budget"])
    if "currency" in data:
        settings["currency"] = data["currency"]
    if "categories" in data:
        settings["categories"] = data["categories"]
    if "scopes" in data:
        settings["scopes"] = data["scopes"]
    if "budget_scopes" in data:
        settings["budget_scopes"] = data["budget_scopes"]
    if "alerts" in data:
        settings["alerts"] = data["alerts"]
    if "theme" in data:
        settings["theme"] = data["theme"]
    
    save_settings(settings)
    return jsonify({"ok": True})


# ============ DELETE TRANSACTION (SOFT DELETE) ============

@app.route("/api/transaction/<tid>", methods=["DELETE"])
@login_required
def api_delete_transaction(tid):
    """Soft delete a transaction by ID (moves to trash)."""
    txns = engine.all()
    match = [t for t in txns if t.id == tid]
    if not match:
        return jsonify({"error": "Transaction not found"}), 404
    
    txn = match[0]
    
    # Move to trash
    trash = load_trash()
    trash.insert(0, {
        "id": tid,
        "deleted_at": datetime.now().isoformat(),
        "transaction": txn_to_dict(txn)
    })
    # Keep only last 100 in trash
    trash = trash[:100]
    save_trash(trash)
    
    # Log the deletion
    save_log("delete", {"transaction_id": tid, "counterparty": txn.counterparty, "amount": txn.amount})
    
    try:
        store.delete([tid])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    return jsonify({"ok": True, "moved_to_trash": True})


@app.route("/api/transactions/bulk-delete", methods=["POST"])
@login_required
def api_bulk_delete():
    """Soft delete multiple transactions (moves to trash)."""
    data = request.get_json() or {}
    ids = data.get("ids", [])
    if not ids:
        return jsonify({"error": "No IDs provided"}), 400
    
    # Move all to trash first
    txns = engine.all()
    trash = load_trash()
    deleted_info = []
    
    for tid in ids:
        match = [t for t in txns if t.id == tid]
        if match:
            txn = match[0]
            trash.insert(0, {
                "id": tid,
                "deleted_at": datetime.now().isoformat(),
                "transaction": txn_to_dict(txn)
            })
            deleted_info.append({"id": tid, "counterparty": txn.counterparty})
    
    trash = trash[:100]  # Keep last 100
    save_trash(trash)
    
    # Log bulk deletion
    save_log("bulk_delete", {"count": len(ids), "transactions": deleted_info[:10]})
    
    try:
        store.delete(ids)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    return jsonify({"ok": True, "deleted": len(ids)})


# ============ ADVANCED STATS ============

@app.route("/api/stats")
@login_required
def api_stats():
    """Return detailed statistics."""
    from collections import defaultdict
    from datetime import timedelta
    
    txns = engine.all()
    settings = load_settings()
    monthly_budget = settings.get("monthly_budget", 10000)
    budget_scopes = settings.get("budget_scopes", ["personal"])
    
    if not txns:
        return jsonify({
            "total_transactions": 0,
            "this_month_transactions": 0,
            "total_spent": 0,
            "total_income": 0,
            "net_flow": 0,
            "avg_transaction": 0,
            "budget_used_percent": 0,
            "budget_remaining": monthly_budget,
            "top_merchants": [],
            "category_breakdown": [],
            "monthly_comparison": {},
            "largest_expense": None,
            "largest_income": None,
            "this_month_spent": 0,
            "last_month_spent": 0,
        })
    
    # Basic stats
    total_spent = sum(t.amount for t in txns if t.direction == "debit")
    total_income = sum(t.amount for t in txns if t.direction == "credit")
    net_flow = total_income - total_spent
    
    # Date range
    dates = [t.datetime for t in txns]
    min_date, max_date = min(dates), max(dates)
    days = max(1, (max_date - min_date).days + 1)
    avg_daily_spend = total_spent / days
    avg_transaction = total_spent / max(1, len([t for t in txns if t.direction == "debit"]))
    
    # This month stats (only count budget_scopes for budget tracking)
    now = datetime.now()
    this_month_txns = [t for t in txns if t.datetime.year == now.year and t.datetime.month == now.month]
    this_month_spent = sum(t.amount for t in this_month_txns if t.direction == "debit" and t.scope in budget_scopes)
    
    # Last month stats (only budget_scopes)
    last_month = now.month - 1 if now.month > 1 else 12
    last_month_year = now.year if now.month > 1 else now.year - 1
    last_month_txns = [t for t in txns if t.datetime.year == last_month_year and t.datetime.month == last_month]
    last_month_spent = sum(t.amount for t in last_month_txns if t.direction == "debit" and t.scope in budget_scopes)
    
    # Budget tracking
    budget_used_percent = min(100, (this_month_spent / monthly_budget) * 100) if monthly_budget > 0 else 0
    budget_remaining = max(0, monthly_budget - this_month_spent)
    
    # Top merchants (by spend)
    merchant_totals = defaultdict(float)
    for t in txns:
        if t.direction == "debit":
            merchant_totals[t.counterparty] += t.amount
    top_merchants = sorted(merchant_totals.items(), key=lambda x: -x[1])[:10]
    
    # Category breakdown
    category_totals = defaultdict(float)
    for t in txns:
        if t.direction == "debit":
            cat = t.category[0] if t.category else "unknown"
            category_totals[cat] += t.amount
    category_breakdown = [{"category": k, "amount": v, "percent": (v / total_spent) * 100 if total_spent > 0 else 0} 
                          for k, v in sorted(category_totals.items(), key=lambda x: -x[1])]
    
    # Monthly comparison
    monthly_totals = defaultdict(lambda: {"spent": 0, "income": 0})
    for t in txns:
        key = t.datetime.strftime("%Y-%m")
        if t.direction == "debit":
            monthly_totals[key]["spent"] += t.amount
        else:
            monthly_totals[key]["income"] += t.amount
    
    # Largest transactions
    debits = [t for t in txns if t.direction == "debit"]
    credits = [t for t in txns if t.direction == "credit"]
    largest_expense = txn_to_dict(max(debits, key=lambda t: t.amount)) if debits else None
    largest_income = txn_to_dict(max(credits, key=lambda t: t.amount)) if credits else None
    
    return jsonify({
        "total_transactions": len(txns),
        "this_month_transactions": len(this_month_txns),
        "total_spent": total_spent,
        "total_income": total_income,
        "net_flow": net_flow,
        "avg_transaction": round(avg_transaction, 2),
        "budget_used_percent": round(budget_used_percent, 1),
        "budget_remaining": round(budget_remaining, 2),
        "monthly_budget": monthly_budget,
        "top_merchants": [{"name": m, "amount": a} for m, a in top_merchants],
        "category_breakdown": category_breakdown,
        "monthly_comparison": dict(sorted(monthly_totals.items())),
        "largest_expense": largest_expense,
        "largest_income": largest_income,
        "this_month_spent": this_month_spent,
        "last_month_spent": last_month_spent,
    })


# ============ ACTIVITY LOGS ============

LOGS_FILE = DATA_PATH.parent / "activity_logs.json"


def load_logs():
    """Load activity logs."""
    import json
    if LOGS_FILE.exists():
        try:
            with open(LOGS_FILE) as f:
                return json.load(f)
        except:
            pass
    return []


def save_log(action, details, user="admin"):
    """Save a new activity log entry."""
    import json
    import uuid
    
    logs = load_logs()
    
    log_entry = {
        "id": f"log_{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "details": details,
        "user": user
    }
    
    logs.insert(0, log_entry)  # Most recent first
    
    # Keep only last 1000 logs
    logs = logs[:1000]
    
    LOGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOGS_FILE, 'w') as f:
        json.dump(logs, f, indent=2)
    
    return log_entry


@app.route("/api/logs")
@login_required
def api_get_logs():
    """Get activity logs with optional filtering."""
    logs = load_logs()
    
    # Filters
    action = request.args.get("action")
    search = request.args.get("search", "").lower()
    limit = int(request.args.get("limit", 100))
    
    if action:
        logs = [l for l in logs if l["action"] == action]
    
    if search:
        logs = [l for l in logs if search in str(l.get("details", "")).lower() 
                or search in l.get("action", "").lower()]
    
    return jsonify({
        "logs": logs[:limit],
        "total": len(logs)
    })


@app.route("/api/logs/clear", methods=["POST"])
@login_required
def api_clear_logs():
    """Clear all activity logs."""
    import json
    LOGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOGS_FILE, 'w') as f:
        json.dump([], f)
    return jsonify({"ok": True})


# ============ SOFT DELETE (TRASH) ============

TRASH_FILE = DATA_PATH.parent / "trash.json"


def load_trash():
    """Load trashed transactions."""
    import json
    if TRASH_FILE.exists():
        try:
            with open(TRASH_FILE) as f:
                return json.load(f)
        except:
            pass
    return []


def save_trash(trash):
    """Save trashed transactions."""
    import json
    TRASH_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRASH_FILE, 'w') as f:
        json.dump(trash, f, indent=2)


@app.route("/api/trash")
@login_required
def api_get_trash():
    """Get trashed transactions."""
    return jsonify(load_trash())


@app.route("/api/trash/restore/<txn_id>", methods=["POST"])
@login_required
def api_restore_transaction(txn_id):
    """Restore a transaction from trash."""
    trash = load_trash()
    
    to_restore = None
    new_trash = []
    for item in trash:
        if item["id"] == txn_id:
            to_restore = item
        else:
            new_trash.append(item)
    
    if not to_restore:
        return jsonify({"error": "Not found in trash"}), 404
    
    # Restore to main store
    from fie.core.transaction import Transaction
    txn_data = to_restore["transaction"]
    txn = Transaction(
        id=txn_data["id"],
        datetime=datetime.fromisoformat(txn_data["datetime"]),
        amount=txn_data["amount"],
        direction=txn_data["direction"],
        counterparty=txn_data["counterparty"],
        category=txn_data.get("category", []),
        scope=txn_data.get("scope", "personal"),
        reviewed=txn_data.get("reviewed", False),
        raw=txn_data.get("raw", "")
    )
    store.add([txn])
    save_trash(new_trash)
    
    save_log("restore", {"transaction_id": txn_id, "counterparty": txn_data["counterparty"]})
    
    return jsonify({"ok": True})


@app.route("/api/trash/empty", methods=["POST"])
@login_required
def api_empty_trash():
    """Permanently delete all trashed items."""
    trash = load_trash()
    count = len(trash)
    save_trash([])
    save_log("empty_trash", {"count": count})
    return jsonify({"ok": True, "deleted": count})


# ============ DATA HEALTH & DUPLICATES ============

@app.route("/api/health")
@login_required
def api_health():
    """Get data health metrics: % reviewed, % auto-tagged, uncategorized count."""
    txns = engine.all()
    total = len(txns)
    if total == 0:
        return jsonify({
            "total": 0,
            "reviewed_count": 0,
            "reviewed_pct": 0,
            "uncategorized_count": 0,
            "uncategorized_pct": 0,
            "top_uncategorized_merchant": None,
            "top_uncategorized_count": 0
        })
    
    reviewed_count = sum(1 for t in txns if t.reviewed)
    uncategorized = [t for t in txns if not t.category or t.category == ["unknown"]]
    uncategorized_count = len(uncategorized)
    
    # Top uncategorized merchant
    merchant_counts = {}
    for t in uncategorized:
        merchant_counts[t.counterparty] = merchant_counts.get(t.counterparty, 0) + 1
    
    top_merchant = None
    top_count = 0
    if merchant_counts:
        top_merchant = max(merchant_counts, key=merchant_counts.get)
        top_count = merchant_counts[top_merchant]
    
    return jsonify({
        "total": total,
        "reviewed_count": reviewed_count,
        "reviewed_pct": round(reviewed_count / total * 100),
        "uncategorized_count": uncategorized_count,
        "uncategorized_pct": round(uncategorized_count / total * 100),
        "top_uncategorized_merchant": top_merchant,
        "top_uncategorized_count": top_count
    })


@app.route("/api/duplicates")
@login_required
def api_duplicates():
    """Find potential duplicate transactions (same merchant, amount ±1, within 2 hours)."""
    txns = engine.all()
    
    # Group potential duplicates
    duplicates = []
    processed = set()
    
    for i, t1 in enumerate(txns):
        if t1.id in processed:
            continue
        
        group = [txn_to_dict(t1)]
        for j, t2 in enumerate(txns[i+1:], i+1):
            if t2.id in processed:
                continue
            
            # Check duplicate criteria
            same_merchant = t1.counterparty.lower() == t2.counterparty.lower()
            similar_amount = abs(t1.amount - t2.amount) <= 1.0
            time_diff = abs((t1.datetime - t2.datetime).total_seconds())
            within_time = time_diff <= 7200  # 2 hours
            
            if same_merchant and similar_amount and within_time:
                group.append(txn_to_dict(t2))
                processed.add(t2.id)
        
        if len(group) > 1:
            duplicates.append({
                "key": f"{t1.counterparty}_{t1.amount}",
                "transactions": group,
                "count": len(group)
            })
            processed.add(t1.id)
    
    return jsonify(duplicates)


@app.route("/api/duplicates/merge", methods=["POST"])
@login_required
def api_merge_duplicates():
    """Keep one transaction, delete the rest."""
    data = request.get_json() or {}
    keep_id = data.get("keep_id")
    delete_ids = data.get("delete_ids", [])
    
    if not keep_id or not delete_ids:
        return jsonify({"error": "Must provide keep_id and delete_ids"}), 400
    
    # Move duplicates to trash
    trash = load_trash()
    deleted_count = 0
    
    for txn_id in delete_ids:
        txn = store.get(txn_id)
        if txn:
            trash.append({
                "id": txn.id,
                "deleted_at": datetime.now().isoformat(),
                "reason": "duplicate_merge",
                "transaction": txn_to_dict(txn)
            })
            store.remove(txn_id)
            deleted_count += 1
    
    save_trash(trash)
    save_log("merge_duplicates", {"kept": keep_id, "deleted": delete_ids})
    
    return jsonify({"ok": True, "deleted": deleted_count})


# ============ CATEGORY DRILLDOWN ============

@app.route("/api/categories/<category>/drilldown")
@login_required
def api_category_drilldown(category):
    """Get detailed breakdown for a category."""
    scope_filter = request.args.get("scope", "personal")
    txns = engine.all()
    
    # Filter by scope and category
    if scope_filter != "all":
        txns = [t for t in txns if t.scope == scope_filter]
    
    cat_txns = [t for t in txns if category in (t.category or [])]
    
    if not cat_txns:
        return jsonify({
            "category": category,
            "total_spent": 0,
            "transaction_count": 0,
            "merchants": [],
            "recent_transactions": []
        })
    
    # Aggregate by merchant
    merchant_data = {}
    for t in cat_txns:
        if t.direction != "debit":
            continue
        m = t.counterparty
        if m not in merchant_data:
            merchant_data[m] = {"name": m, "amount": 0, "count": 0}
        merchant_data[m]["amount"] += t.amount
        merchant_data[m]["count"] += 1
    
    # Sort merchants by amount
    merchants = sorted(merchant_data.values(), key=lambda x: -x["amount"])
    for m in merchants:
        m["avg_amount"] = round(m["amount"] / m["count"]) if m["count"] > 0 else 0
    
    # Total spent (debits only)
    total_spent = sum(t.amount for t in cat_txns if t.direction == "debit")
    
    # Recent transactions (last 10)
    recent = sorted(cat_txns, key=lambda t: t.datetime, reverse=True)[:10]
    recent_data = [{
        "id": t.id,
        "date": t.datetime.strftime("%Y-%m-%d"),
        "merchant": t.counterparty,
        "amount": t.amount,
        "direction": t.direction
    } for t in recent]
    
    return jsonify({
        "category": category,
        "total_spent": total_spent,
        "transaction_count": len(cat_txns),
        "merchants": merchants[:10],  # Top 10
        "recent_transactions": recent_data
    })


# ============ SAVED FILTERS ============

FILTERS_FILE = DATA_PATH.parent / "saved_filters.json"


def load_saved_filters():
    """Load saved filter presets."""
    import json
    if FILTERS_FILE.exists():
        try:
            with open(FILTERS_FILE) as f:
                return json.load(f)
        except:
            pass
    return []


def save_filters_to_file(filters):
    """Save filter presets to file."""
    import json
    FILTERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(FILTERS_FILE, 'w') as f:
        json.dump(filters, f, indent=2)


@app.route("/api/filters")
@login_required
def api_get_filters():
    """Get saved filter presets."""
    return jsonify(load_saved_filters())


@app.route("/api/filters", methods=["POST"])
@login_required
def api_save_filter():
    """Save a new filter preset."""
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    filters = data.get("filters", {})
    
    if not name:
        return jsonify({"error": "Name required"}), 400
    
    saved = load_saved_filters()
    
    # Generate ID
    import uuid
    new_filter = {
        "id": str(uuid.uuid4())[:8],
        "name": name,
        "filters": filters,
        "created_at": datetime.now().isoformat()
    }
    
    saved.append(new_filter)
    save_filters_to_file(saved)
    
    return jsonify({"ok": True, "filter": new_filter})


@app.route("/api/filters/<filter_id>", methods=["DELETE"])
@login_required
def api_delete_filter(filter_id):
    """Delete a saved filter preset."""
    saved = load_saved_filters()
    saved = [f for f in saved if f["id"] != filter_id]
    save_filters_to_file(saved)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)