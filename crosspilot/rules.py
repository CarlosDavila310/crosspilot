"""Deterministic business rules. The LLM never overrides anything decided here."""

APROBADO, CONTRAOFERTA, VETO = "APROBADO", "CONTRAOFERTA", "VETO"
MAX_OFFER_ITEMS = 2


def fmt_soles(amount):
    return f"S/ {int(amount):,}"


def is_credit(state, product_id):
    product = state["catalog"].get(product_id)
    return bool(product) and product["type"] == "credito"


def _result(approved, max_amount, reasons):
    return {"approved": approved, "max_amount": max_amount, "reasons": reasons}


def check_policy(state, client_id, product_id, amount=None):
    """Design §6.1. Returns {"approved", "max_amount", "reasons"}."""
    policy = state["policy"]
    client, product = state["clients"].get(client_id), state["catalog"].get(product_id)
    if not client or not product:
        return _result(False, 0, ["cliente o producto inexistente"])
    if product_id in client["products"]:
        return _result(False, 0, ["el cliente ya tiene este producto"])
    if product["type"] != "credito":
        return _result(True, None, [])
    late = client["max_days_late_12m"]
    if late > policy["max_days_late"]:
        return _result(False, 0, [f"atraso de {late} días en 12 meses (máximo {policy['max_days_late']})"])
    headroom = policy["debt_multiple"] * client["monthly_net_income"] - client["current_debt"]
    round_to = policy["round_to"]
    max_amount = max(0, int(min(headroom, product["max_amount"]) // round_to * round_to))
    if max_amount < product["min_amount"]:
        return _result(False, 0, ["sin capacidad de endeudamiento suficiente"])
    if amount is None:
        return _result(False, max_amount, ["falta el monto"])
    if amount < product["min_amount"]:
        return _result(False, max_amount, [f"monto menor al mínimo del producto ({fmt_soles(product['min_amount'])})"])
    if amount > max_amount:
        return _result(False, max_amount, [f"excede el límite de endeudamiento: máximo {fmt_soles(max_amount)}"])
    return _result(True, max_amount, [])


def decide(state, product_id, check):
    """Derived decision used by the orchestrator (design §6.1)."""
    if check["approved"]:
        return APROBADO
    product = state["catalog"].get(product_id)
    if is_credit(state, product_id) and check["max_amount"] and check["max_amount"] >= product["min_amount"]:
        return CONTRAOFERTA
    return VETO


def validate_offer(state, client_id, items):
    """Design §6.3. Returns (kept, dropped); dropped items carry the reason."""
    client = state["clients"][client_id]
    kept, dropped, seen, credits = [], [], set(), 0
    for item in items:
        pid, amount = item.get("product_id"), item.get("amount")
        reason = None
        if pid not in state["catalog"]:
            reason = "no existe en el catálogo"
        elif pid in client["products"]:
            reason = "el cliente ya lo tiene"
        elif pid in seen:
            reason = "producto repetido"
        elif is_credit(state, pid) and not (isinstance(amount, int) and not isinstance(amount, bool) and amount > 0):
            reason = "crédito sin monto válido"
        elif is_credit(state, pid) and credits >= 1:
            reason = "solo un crédito por oferta: la capacidad de endeudamiento es una sola"
        elif len(kept) >= MAX_OFFER_ITEMS:
            reason = f"la oferta admite como máximo {MAX_OFFER_ITEMS} productos"
        if reason:
            dropped.append({"product_id": pid, "reason": reason})
            continue
        seen.add(pid)
        credits += is_credit(state, pid)
        kept.append(item)
    return kept, dropped


def bank_products(state):
    """Bank catalog ids, in catalog order. Partner products are not part of credit risk or ranking."""
    return [pid for pid, p in state["catalog"].items() if p["type"] != "aliado"]


def eligible_products(state, client_id):
    """Bank products the client lacks and that check_policy would not veto."""
    # amount=None: an eligible credit comes back as CONTRAOFERTA for its max amount.
    return [pid for pid in bank_products(state)
            if decide(state, pid, check_policy(state, client_id, pid)) != VETO]


def rank_clients(state, n=5):
    """Design §6.2: best eligible credit margin + all eligible non-credit margins."""
    ranking = []
    for cid in state["clients"]:
        eligible = eligible_products(state, cid)
        margin = lambda pid: state["catalog"][pid]["annual_margin"]
        credits = [margin(pid) for pid in eligible if is_credit(state, pid)]
        others = [margin(pid) for pid in eligible if not is_credit(state, pid)]
        ranking.append({"client_id": cid, "score": max(credits, default=0) + sum(others), "eligible": eligible})
    ranking.sort(key=lambda r: (-r["score"], r["client_id"]))
    return ranking[:n]
