"""Orchestrator (design §8, requirements_v2 §2). Plain code, not an LLM."""
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from crosspilot import agents, rules
from crosspilot.llm import AgentError

ORQ, VC, RISK = "ORQUESTADOR", "VENTA CRUZADA", "RIESGO"
PENDING, NO_OFFER = "PENDIENTE_APROBACION", "SIN_OFERTA"


def _name(state, pid):
    return state["catalog"][pid]["name"]


def _item_text(state, item):
    amount = f" por {rules.fmt_soles(item['amount'])}" if item.get("amount") is not None else ""
    return f"• {_name(state, item['product_id'])}{amount}: {item.get('reason', '')}"


def _closing(state, final, decisions):
    if not final:
        return "No hay oferta viable para este cliente hoy."
    counter = next((d for d in decisions if d["decision"] == rules.CONTRAOFERTA), None)
    vetoed = [d for d in decisions if d["decision"] == rules.VETO]
    if counter:
        return (f"Acepto la contraoferta de Riesgo: {_name(state, counter['product_id']).lower()} por "
                f"{rules.fmt_soles(counter['max_amount'])}. Pasa a aprobación del ejecutivo.")
    if vetoed:
        gone = " y ".join(_name(state, d["product_id"]).lower() for d in vetoed)
        kept = " y ".join(_name(state, d["product_id"]).lower() for d in final)
        return f"Riesgo vetó {gone}. Sigue {kept}. Pasa a aprobación del ejecutivo."
    return "Riesgo aprobó la oferta completa. Pasa a aprobación del ejecutivo."


def run_pipeline(state, client_id, fake=False, on_stage=None, pace=0):
    """Cross-sell proposes, rules validate, Risk explains, code closes. Reads `state`, never mutates it."""
    stage = on_stage or (lambda cid, name: None)
    client = state["clients"][client_id]
    log = [{"sender": ORQ, "text": f"Preparo la visita a {client['name']}: buscamos el siguiente producto."}]

    stage(client_id, "cross_sell")
    offer = agents.cross_sell(state, client_id, fake=fake, pace=pace)
    kept, dropped = rules.validate_offer(state, client_id, offer.get("items", []))
    pitch = offer.get("pitch", "")
    log.append({"sender": VC, "text": "\n".join([f"“{pitch}”"] + [_item_text(state, i) for i in offer.get("items", [])])})
    for d in dropped:
        product = state["catalog"].get(d["product_id"], {}).get("name", d["product_id"])
        log.append({"sender": ORQ, "text": f"Descarté {product}: {d['reason']}."})

    result = {"client_id": client_id, "pitch": pitch, "proposed": offer.get("items", []), "dropped": dropped}
    if not kept:
        log.append({"sender": ORQ, "text": "No hay oferta viable para este cliente hoy."})
        return {**result, "status": NO_OFFER, "items": [], "decisions": [], "vetoes": 0, "log": log,
                "closing": "No hay oferta viable para este cliente hoy."}

    decisions = []
    for item in kept:
        check = rules.check_policy(state, client_id, item["product_id"], item.get("amount"))
        decisions.append({**item, "decision": rules.decide(state, item["product_id"], check),
                          "proposed_amount": item.get("amount"), "max_amount": check["max_amount"],
                          "explanation": "; ".join(check["reasons"]) or "Cumple la política."})

    stage(client_id, "risk")
    review = agents.risk_review(state, client_id, kept, fake=fake, pace=pace)
    texts = {e["product_id"]: e["explanation"] for e in review.get("explanations", []) if e.get("explanation")}
    for d in decisions:
        d["explanation"] = texts.get(d["product_id"], d["explanation"])
    log.append({"sender": RISK, "text": "\n".join(
        f"{d['decision']} · {_name(state, d['product_id'])}: {d['explanation']}" for d in decisions)})

    final = [{**d, "amount": d["max_amount"]} if d["decision"] == rules.CONTRAOFERTA else dict(d)
             for d in decisions if d["decision"] != rules.VETO]
    closing = _closing(state, final, decisions)
    log.append({"sender": ORQ, "text": closing})
    return {**result, "status": PENDING if final else NO_OFFER, "items": final, "decisions": decisions,
            "vetoes": sum(d["decision"] == rules.VETO for d in decisions), "log": log, "closing": closing}


def run_one(state, client_id, fake=False, on_stage=None, pace=0):
    """Wraps run_pipeline so one failing client never breaks the others (V1.4)."""
    try:
        return {"status": "done", "result": run_pipeline(state, client_id, fake, on_stage, pace)}
    except AgentError as exc:
        return {"status": "error", "error": str(exc)}
    except Exception:  # shortcut: generic message for unexpected bugs; log them once there is telemetry
        return {"status": "error", "error": "Los agentes no respondieron"}


def run_portfolio(state, client_ids=None, fake=False, on_stage=None, on_done=None, on_tick=None, pace=0):
    """Requirements_v2 V1.1: every client in parallel. Returns {client_id: run}.

    `on_stage` runs in worker threads (keep it thread-safe); `on_done` and `on_tick` run in the caller's thread.
    """
    client_ids = list(client_ids or state["clients"])
    runs = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        pending = {pool.submit(run_one, state, cid, fake, on_stage, pace): cid for cid in client_ids}
        while pending:
            done, _ = wait(pending, timeout=0.2, return_when=FIRST_COMPLETED)
            for future in done:
                cid = pending.pop(future)
                runs[cid] = future.result()
                if on_done:
                    on_done(cid, runs[cid])
            if on_tick:
                on_tick()
    return runs
