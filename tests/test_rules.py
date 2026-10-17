from crosspilot.data import new_state, products_per_client
from crosspilot.rules import APROBADO, CONTRAOFERTA, VETO, check_policy, decide, validate_offer


def test_seed_starts_at_2_2_products_per_client():
    assert products_per_client(new_state()) == 2.2


def test_new_state_returns_independent_copies():
    a, b = new_state(), new_state()
    a["clients"]["C01"]["products"].append("cobro_qr")
    a["stats"]["vetoes"] += 1
    a["crm"].append({})
    assert "cobro_qr" not in b["clients"]["C01"]["products"]
    assert b["stats"]["vetoes"] == 0
    assert b["crm"] == []
    assert "cobro_qr" not in new_state()["clients"]["C01"]["products"]


def test_seed_products_exist_in_catalog():
    state = new_state()
    for client in state["clients"].values():
        assert set(client["products"]) <= set(state["catalog"])


def _decision(state, cid, pid, amount):
    return decide(state, pid, check_policy(state, cid, pid, amount))


def test_c01_fixed_asset_20000_is_counteroffer_of_12000():
    state = new_state()
    check = check_policy(state, "C01", "credito_activo_fijo", 20000)
    assert check["approved"] is False
    assert check["max_amount"] == 12000
    assert decide(state, "credito_activo_fijo", check) == CONTRAOFERTA


def test_c01_15000_is_blocked_and_12000_passes():
    state = new_state()
    assert check_policy(state, "C01", "credito_activo_fijo", 15000)["approved"] is False
    assert check_policy(state, "C01", "credito_activo_fijo", 12000)["approved"] is True


def test_c03_credit_is_vetoed_for_late_payments():
    state = new_state()
    for pid in ("credito_activo_fijo", "credito_capital_trabajo"):
        assert _decision(state, "C03", pid, 5000) == VETO
    assert "atraso de 25 días" in check_policy(state, "C03", "credito_activo_fijo", 5000)["reasons"][0]


def test_non_credit_product_not_owned_is_approved():
    state = new_state()
    assert check_policy(state, "C01", "seguro_negocio") == {"approved": True, "max_amount": None, "reasons": []}
    assert _decision(state, "C01", "seguro_negocio", None) == APROBADO


def test_owned_product_is_vetoed():
    state = new_state()
    check = check_policy(state, "C01", "cuenta_ahorro")
    assert check["approved"] is False
    assert decide(state, "cuenta_ahorro", check) == VETO


def test_no_headroom_is_vetoed():
    state = new_state()  # C06: 6 x 2,000 - 12,000 = 0
    assert _decision(state, "C06", "credito_capital_trabajo", 1000) == VETO


def test_validate_offer_drops_owned_unknown_second_credit_and_credit_without_amount():
    state = new_state()
    kept, dropped = validate_offer(state, "C05", [
        {"product_id": "cuenta_ahorro", "amount": None},
        {"product_id": "producto_fantasma", "amount": None},
        {"product_id": "credito_activo_fijo", "amount": None},
        {"product_id": "credito_activo_fijo", "amount": 5000},
        {"product_id": "credito_capital_trabajo", "amount": 2000},
        {"product_id": "seguro_negocio", "amount": None},
    ])
    assert [i["product_id"] for i in kept] == ["credito_activo_fijo", "seguro_negocio"]
    reasons = {d["product_id"] + ":" + d["reason"] for d in dropped}
    assert "cuenta_ahorro:el cliente ya lo tiene" in reasons
    assert "producto_fantasma:no existe en el catálogo" in reasons
    assert "credito_activo_fijo:crédito sin monto válido" in reasons
    assert any(r.startswith("credito_capital_trabajo:solo un crédito") for r in reasons)


def test_validate_offer_caps_at_two_items_and_drops_repeats():
    state = new_state()
    kept, dropped = validate_offer(state, "C02", [
        {"product_id": "seguro_negocio", "amount": None},
        {"product_id": "seguro_negocio", "amount": None},
        {"product_id": "credito_capital_trabajo", "amount": 3000},
        {"product_id": "credito_activo_fijo", "amount": 6000},
    ])
    assert [i["product_id"] for i in kept] == ["seguro_negocio", "credito_capital_trabajo"]
    assert [d["reason"] for d in dropped][0] == "producto repetido"
    assert len(dropped) == 2
