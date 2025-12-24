"""
FIE Default Configuration
========================
All default values for the application. These can be overridden by user settings.
This file serves as the single source of truth for initial/default configurations.

Usage:
    from fie.defaults import DEFAULT_RULES, DEFAULT_SETTINGS, DEFAULT_CATEGORIES
"""

# ============================================================================
# DEFAULT CATEGORIES
# ============================================================================
DEFAULT_CATEGORIES = [
    "food", "delivery", "groceries", "shopping", "commute", "cab", "auto",
    "utilities", "recharge", "entertainment", "subscriptions", "health",
    "education", "transfer", "splits", "refund", "deposit", "income",
    "coffee", "snacks", "daily", "noise", "unknown"
]

# ============================================================================
# DEFAULT SCOPES
# ============================================================================
DEFAULT_SCOPES = ["personal", "family", "education", "shared"]

# ============================================================================
# DEFAULT SETTINGS
# ============================================================================
DEFAULT_SETTINGS = {
    "monthly_budget": 10000,
    "currency": "₹",
    "categories": DEFAULT_CATEGORIES,
    "scopes": DEFAULT_SCOPES,
    "budget_scopes": ["personal"],  # Which scopes count toward budget
    "alerts": {
        "budget_warning_percent": 80,
        "large_transaction_threshold": 5000
    },
    "theme": "dark",
    "credits_config": {
        "split_max_amount": 2000,  # Credits ≤ this are considered splits/refunds
        "split_categories": ["splits", "refund", "split", "payback"],  # Categories that indicate splits
    }
}

# ============================================================================
# DEFAULT AUTO-TAGGING RULES
# ============================================================================
# Priority: Lower number = higher priority (checked first)
# Rules are checked in order; first match wins

DEFAULT_RULES = [
    # === MERCHANT-BASED RULES (higher priority - more specific) ===
    {
        "id": "rule_food_delivery",
        "name": "Food Delivery",
        "description": "Swiggy, Zomato, Uber Eats, Dunzo",
        "type": "merchant",
        "enabled": True,
        "priority": 1,
        "conditions": {"merchant_contains": "swiggy, zomato, uber eats, dunzo"},
        "actions": {"scope": "personal", "category": ["food"]}
    },
    {
        "id": "rule_yulu",
        "name": "Yulu Bikes",
        "description": "Yulu bike rentals",
        "type": "merchant",
        "enabled": True,
        "priority": 2,
        "conditions": {"merchant_contains": "yulu"},
        "actions": {"scope": "personal", "category": ["commute"]}
    },
    {
        "id": "rule_rapido_ola_uber",
        "name": "Cab/Auto Apps",
        "description": "Rapido, Ola, Uber, Namma Yatri",
        "type": "merchant",
        "enabled": True,
        "priority": 3,
        "conditions": {"merchant_contains": "rapido, ola, uber, namma yatri"},
        "actions": {"scope": "personal", "category": ["cab"]}
    },
    {
        "id": "rule_online_shopping",
        "name": "Online Shopping",
        "description": "Amazon, Flipkart, Myntra, Blinkit, Meesho",
        "type": "merchant",
        "enabled": True,
        "priority": 4,
        "conditions": {"merchant_contains": "amazon, amzn, flipkart, myntra, blinkit, meesho"},
        "actions": {"scope": "personal", "category": ["shopping"]}
    },
    {
        "id": "rule_groceries",
        "name": "Groceries",
        "description": "BigBasket, Zepto, Instamart, JioMart",
        "type": "merchant",
        "enabled": True,
        "priority": 5,
        "conditions": {"merchant_contains": "bigbasket, zepto, instamart, jiomart"},
        "actions": {"scope": "personal", "category": ["groceries"]}
    },
    {
        "id": "rule_electricity",
        "name": "Electricity",
        "description": "Electricity bills (BESCOM, etc.)",
        "type": "merchant",
        "enabled": True,
        "priority": 6,
        "conditions": {"merchant_contains": "bescom, electricity, power"},
        "actions": {"scope": "family", "category": ["utilities"]}
    },
    {
        "id": "rule_mobile_recharge",
        "name": "Mobile Recharge",
        "description": "Airtel, Jio, Vi, BSNL recharges",
        "type": "merchant",
        "enabled": True,
        "priority": 7,
        "conditions": {"merchant_contains": "airtel, jio, vi, vodafone, bsnl, recharge"},
        "actions": {"scope": "personal", "category": ["recharge"]}
    },
    
    # === CREDIT RULES (categorize incoming money) ===
    {
        "id": "rule_split_refund",
        "name": "Split/Refund",
        "description": "Small credits from friends (up to 2000)",
        "type": "combined",
        "enabled": True,
        "priority": 10,
        "conditions": {"amount_min": 1, "amount_max": 2000, "direction": "credit"},
        "actions": {"scope": "personal", "category": ["splits"]}
    },
    {
        "id": "rule_deposit",
        "name": "Deposit/Income",
        "description": "Large credits (2001+) - parents, salary",
        "type": "combined",
        "enabled": True,
        "priority": 11,
        "conditions": {"amount_min": 2001, "direction": "credit"},
        "actions": {"scope": "personal", "category": ["deposit"]}
    },
    
    # === AMOUNT-BASED RULES (lower priority - fallback for debits) ===
    {
        "id": "rule_noise",
        "name": "Noise",
        "description": "Micro transactions 0-10",
        "type": "amount",
        "enabled": True,
        "priority": 20,
        "conditions": {"amount_min": 0, "amount_max": 10, "direction": "debit"},
        "actions": {"scope": "personal", "category": ["noise"]}
    },
    {
        "id": "rule_coffee",
        "name": "Coffee",
        "description": "Small purchases 11-25",
        "type": "amount",
        "enabled": True,
        "priority": 21,
        "conditions": {"amount_min": 11, "amount_max": 25, "direction": "debit"},
        "actions": {"scope": "personal", "category": ["coffee"]}
    },
    {
        "id": "rule_snacks",
        "name": "Snacks",
        "description": "Medium purchases 26-50",
        "type": "amount",
        "enabled": True,
        "priority": 22,
        "conditions": {"amount_min": 26, "amount_max": 50, "direction": "debit"},
        "actions": {"scope": "personal", "category": ["snacks"]}
    },
    {
        "id": "rule_daily",
        "name": "Daily",
        "description": "Daily expenses 51-100",
        "type": "amount",
        "enabled": True,
        "priority": 23,
        "conditions": {"amount_min": 51, "amount_max": 100, "direction": "debit"},
        "actions": {"scope": "personal", "category": ["daily"]}
    },
]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_default_rules():
    """Return a fresh copy of default rules (to avoid mutation)."""
    import copy
    return copy.deepcopy(DEFAULT_RULES)


def get_default_settings():
    """Return a fresh copy of default settings."""
    import copy
    return copy.deepcopy(DEFAULT_SETTINGS)


def get_split_categories():
    """Get categories that indicate split/refund transactions."""
    return set(DEFAULT_SETTINGS["credits_config"]["split_categories"])


def get_split_max_amount():
    """Get max amount threshold for auto-classifying as split."""
    return DEFAULT_SETTINGS["credits_config"]["split_max_amount"]
