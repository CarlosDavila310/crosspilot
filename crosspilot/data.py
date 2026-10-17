import copy
import json
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
