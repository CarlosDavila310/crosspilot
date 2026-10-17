from crosspilot.data import new_state, products_per_client


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
