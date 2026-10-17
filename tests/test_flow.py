from crosspilot import agents, fakes
from crosspilot.data import new_state, projected_products_per_client
from crosspilot.llm import AgentError
from crosspilot.orchestrator import ORQ, RISK, VC, run_pipeline, run_portfolio
from crosspilot.rules import priority_score, validate_approval


def test_pipeline_c01_counteroffer_and_log_order():
    result = run_pipeline(new_state(), "C01", fake=True)
    assert result["status"] == "PENDIENTE_APROBACION"
    assert [(i["product_id"], i["amount"]) for i in result["items"]] == [
        ("credito_activo_fijo", 12000), ("seguro_negocio", None)]
    senders = [m["sender"] for m in result["log"]]
    assert senders[0] == ORQ and senders[-1] == ORQ
    assert VC in senders and RISK in senders
    assert "S/ 12,000" in result["log"][-1]["text"]


def test_pipeline_c03_vetoes_credit_and_keeps_insurance():
    result = run_pipeline(new_state(), "C03", fake=True)
    assert [d["decision"] for d in result["decisions"]] == ["VETO", "APROBADO"]
    assert [i["product_id"] for i in result["items"]] == ["seguro_negocio"]
    assert result["vetoes"] == 1


def test_pipeline_without_viable_offer():
    result = run_pipeline(new_state(), "C08", fake=True)
    assert result["status"] == "SIN_OFERTA"
    assert result["items"] == []


def test_portfolio_runs_in_parallel_and_c01_is_first_with_85():
    state = new_state()
    runs = run_portfolio(state, fake=True)
    assert set(runs) == set(state["clients"])
    assert all(r["status"] == "done" for r in runs.values())
    scores = {cid: priority_score(state, cid, r["result"]) for cid, r in runs.items()}
    assert scores["C01"] == 85
    assert max(scores, key=lambda cid: (scores[cid], -int(cid[1:]))) == "C01"


def test_portfolio_isolates_agent_errors(monkeypatch):
    original = agents.risk_review

    def flaky(state, client_id, items, fake=False, pace=0):
        if client_id == "C05":
            raise AgentError("risk")
        return original(state, client_id, items, fake=fake, pace=pace)

    monkeypatch.setattr(agents, "risk_review", flaky)
    runs = run_portfolio(new_state(), fake=True)
    assert runs["C05"] == {"status": "error", "error": "Riesgo no respondió"}
    assert sum(r["status"] == "done" for r in runs.values()) == 9


def test_approval_revalidates_amounts():
    state = new_state()
    over = [{"product_id": "credito_activo_fijo", "amount": 15000}, {"product_id": "seguro_negocio", "amount": None}]
    assert validate_approval(state, "C01", over) == [
        "Crédito activo fijo: excede el límite de endeudamiento: máximo S/ 12,000."]
    over[0]["amount"] = 12000
    assert validate_approval(state, "C01", over) == []
    assert validate_approval(state, "C01", []) == ["Incluye al menos un producto para aprobar."]
    two_credits = [{"product_id": "credito_activo_fijo", "amount": 6000}, {"product_id": "credito_capital_trabajo", "amount": 1000}]
    assert "Solo se ofrece un crédito" in validate_approval(state, "C02", two_credits)[0]


def test_projected_products_per_client():
    assert projected_products_per_client(new_state(), 2) == 2.4


def test_brief_and_chat_in_fake_mode():
    state = new_state()
    result = run_pipeline(state, "C01", fake=True)
    brief = agents.visit_brief(state, "C01", result["items"], result["pitch"], fake=True)
    assert len(brief["talking_points"]) == 3 and len(brief["objeciones"]) == 2
    assert "S/ 12,000" in brief["talking_points"][0]
    reply = agents.chat_reply(state, "C01", "risk", "¿Y si subo a S/ 15,000?", [], result, fake=True)
    assert reply.startswith("No: con S/ 15,000 excede")
    reply = agents.chat_reply(state, "C01", "cross_sell", "¿Y del ecosistema?", [], result, fake=True)
    assert "Pacífico Seguros" in reply and "Mibanco" not in reply


def test_fake_offers_cover_every_client():
    assert set(fakes.OFFERS) == set(new_state()["clients"])
