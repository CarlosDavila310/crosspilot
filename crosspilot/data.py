import copy
import json
import math
from pathlib import Path

SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "seed.json"
_SEED = json.loads(SEED_PATH.read_text(encoding="utf-8"))


def new_state():
    """Fresh session state: deep copy of the seed plus empty CRM and counters."""
    state = copy.deepcopy(_SEED)
    state["crm"] = []
    state["stats"] = {"approved_offers": 0, "accepted_products": 0, "vetoes": 0}
    return state


def products_per_client(state):
    clients = state["clients"].values()
    return round(sum(len(c["products"]) for c in clients) / len(clients), 1)


def projected_products_per_client(state, approved_products):
    """Products per client if every approved product is accepted (requirements_v2 §6)."""
    clients = state["clients"].values()
    total = sum(len(c["products"]) for c in clients) + approved_products
    return round(total / len(clients), 1)


MONTHS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Set", "Oct", "Nov", "Dic"]


def month_label(t):
    """Month t of the 24-month window that starts in Oct 2024."""
    return f"{MONTHS[(9 + t) % 12]} {24 + (9 + t) // 12}"


def client_history(state, client_id):
    """Synthetic 24-month series for the profile charts (same formulas as the v2 design prototype)."""
    client = state["clients"][client_id]
    share, debt, saving = client["principality"], client["current_debt"], client["savings_balance"]
    debt_series = [max(0.0, debt * (0.55 + 0.45 * t / 23) * (1 + 0.06 * math.sin(t * 1.3))) for t in range(24)]
    has_savings = "cuenta_ahorro" in client["products"] and saving > 0
    savings = [saving * (0.7 + 0.3 * t / 23) * (1.25 if (9 + t) % 12 == 11 else 1) for t in range(24)]
    late = [0] * 12
    if client["max_days_late_12m"] > 0:
        i = int(client_id[1:]) % 12
        late[i] = client["max_days_late_12m"]
        late[(i + 5) % 12] = client["max_days_late_12m"] // 3
    return {
        "months": [month_label(t) for t in range(24)],
        "debt_bank": [round(v * share) for v in debt_series],
        "debt_other": [round(v * (1 - share)) for v in debt_series],
        "savings": [round(v) for v in savings] if has_savings else [],
        "late_months": [month_label(12 + i) for i in range(12)],
        "late_days": late,
    }
