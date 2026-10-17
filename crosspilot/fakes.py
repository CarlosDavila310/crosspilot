"""Backup-mode answers (design §11 + design/Crosspilot v2 `FAKE`, `makeBrief`, `answer`).

Same shape as each agent's submit tool. Never calls the network.
"""
import re
import time

from crosspilot import rules

CT, AF, SG, AH, QR = "credito_capital_trabajo", "credito_activo_fijo", "seguro_negocio", "cuenta_ahorro", "cobro_qr"


def _item(pid, amount, reason):
    return {"product_id": pid, "amount": amount, "reason": reason}


OFFERS = {
    "C01": ("Financiar la remalladora y proteger el taller.",
            [_item(AF, 20000, "Cotizó una remalladora industrial de S/ 20,000."), _item(SG, None, "Su maquinaria no tiene seguro.")]),
    "C02": ("Más stock para diciembre y el local protegido.",
            [_item(CT, 10000, "Sus ventas suben en diciembre."), _item(SG, None, "Su local no tiene seguro.")]),
    "C03": ("Ampliar la cocina y asegurar el local.",
            [_item(AF, 15000, "Quiere ampliar la cocina."), _item(SG, None, "Su local no tiene seguro contra incendio.")]),
    "C04": ("Stock para la temporada de obras y cobros con QR.",
            [_item(CT, 7000, "Compra cemento y fierro antes de la temporada de obras."), _item(QR, None, "Sus clientes le piden pagar con QR.")]),
    "C05": ("Insumos para fiestas y equipos protegidos.",
            [_item(CT, 2000, "Compra insumos para la campaña de fiestas."), _item(SG, None, "Sus equipos de peluquería no tienen seguro.")]),
    "C06": ("Proteger el taller y ordenar su efectivo.",
            [_item(SG, None, "Su taller no tiene seguro."), _item(AH, None, "Guarda el efectivo del día en el local.")]),
    "C07": ("Financiar el segundo camión de reparto.",
            [_item(AF, 26000, "Quiere comprar un segundo camión de reparto.")]),
    "C08": ("Financiar la cepilladora.",
            [_item(AF, 8000, "Cotizó una cepilladora industrial.")]),
    "C09": ("Guardar el efectivo de la tienda en el banco.",
            [_item(AH, None, "Deja el efectivo de la tienda en caja.")]),
    "C10": ("Proteger las máquinas y cobrar con QR.",
            [_item(SG, None, "Sus máquinas no tienen seguro."), _item(QR, None, "Sus clientes corporativos piden pagar con QR.")]),
}

RISK_C01 = {
    AF: "Con S/ 20,000 su deuda superaría 6 veces su ingreso mensual. Máximo sano: S/ 12,000.",
    SG: "No tiene seguro de negocio. No suma deuda.",
}


def _pace(ctx, share):
    """Staggered fake latency so the parallel run is visible in the demo; 0 in tests."""
    pace = ctx.get("pace", 0)
    if pace:
        index = int(ctx["client_id"][1:])
        time.sleep(pace * share * (0.9 + (index * 37 % 10) * 0.28))


def _cross_sell(ctx):
    cid = ctx["client_id"]
    if cid in OFFERS:
        pitch, items = OFFERS[cid]
        return {"pitch": pitch, "items": [dict(i) for i in items]}
    state = ctx["state"]
    eligible = [p for p in rules.eligible_products(state, cid) if not rules.is_credit(state, p)]
    return {"pitch": "Completar su relación con el banco.",
            "items": [_item(p, None, "No lo tiene todavía.") for p in eligible[:2]] or [_item(CT, None, "Sin elegibles.")]}


def explain(state, client_id, product_id, decision, check, amount):
    client = state["clients"][client_id]
    late, limit = client["max_days_late_12m"], state["policy"]["max_days_late"]
    if not rules.is_credit(state, product_id):
        return "No lo tiene y no suma deuda. Venta sana."
    if decision == rules.VETO:
        if late > limit:
            return f"Tuvo {late} días de atraso en 12 meses; la política permite {limit}. No se ofrece crédito."
        return "Sin capacidad de endeudamiento suficiente para el monto mínimo."
    if decision == rules.CONTRAOFERTA:
        return (f"Con {rules.fmt_soles(amount)} su deuda superaría {state['policy']['debt_multiple']} veces su "
                f"ingreso mensual. Máximo sano: {rules.fmt_soles(check['max_amount'])}.")
    return "Dentro de su capacidad de endeudamiento."


def _risk(ctx):
    state, cid = ctx["state"], ctx["client_id"]
    out = []
    for item in ctx["items"]:
        pid, amount = item["product_id"], item.get("amount")
        check = rules.check_policy(state, cid, pid, amount)
        text = (cid == "C01" and RISK_C01.get(pid)) or explain(state, cid, pid, rules.decide(state, pid, check), check, amount)
        out.append({"product_id": pid, "explanation": text})
    return {"explanations": out}


def _brief(ctx):
    state, cid, items = ctx["state"], ctx["client_id"], ctx["items"]
    client = state["clients"][cid]
    oferta = [state["catalog"][i["product_id"]]["name"] + (f" por {rules.fmt_soles(i['amount'])}" if i.get("amount") else "")
              for i in items]
    credit = next((i for i in items if rules.is_credit(state, i["product_id"])), None)
    if cid == "C01":
        points = []
        if credit:
            points.append(f"La remalladora que cotizó sube su producción; el crédito por {rules.fmt_soles(credit['amount'])} cubre la mayor parte.")
        if any(i["product_id"] == SG for i in items):
            points.append("Su maquinaria no tiene seguro: un robo o un incendio pararía el taller.")
        points += ["Ya cobra por QR de otros bancos; más adelante puede concentrar sus cobros aquí.",
                   "Es puntual: 3 días de atraso máximo en el último año."]
        first = ({"objecion": f"{rules.fmt_soles(credit['amount'])} no me alcanza para la máquina.",
                  "respuesta": "Financiamos hasta su capacidad sana de pago. La diferencia puede cubrirla con su ahorro o una cuota inicial."}
                 if credit else
                 {"objecion": "Prefiero esperar para la máquina.",
                  "respuesta": "Revisamos el crédito en la próxima visita, con su capacidad actualizada."})
        return {"resumen": "Taller de confección en La Victoria. Clienta puntual, con capital de trabajo y cuenta de ahorro.",
                "oferta": oferta, "talking_points": points[:3],
                "objeciones": [first, {"objecion": "El seguro es un gasto extra.",
                                       "respuesta": "La prima es baja frente al costo de reponer una máquina de S/ 20,000."}],
                "siguiente_paso": ("Llevar la solicitud prellenada y la cotización; agendar el desembolso en 48 horas."
                                   if credit else "Activar el seguro durante la visita.")}
    points = [s + "." for s in client["signals"]] + [f"Hoy tiene {len(client['products'])} producto(s) con el banco."]
    good = client["max_days_late_12m"] <= state["policy"]["max_days_late"]
    if credit:
        objections = [{"objecion": "La cuota me preocupa.",
                       "respuesta": "El monto ya está dentro de su capacidad. Elegimos juntos una cuota que calce con sus ventas."},
                      {"objecion": "Ya trabajo con otro banco.",
                       "respuesta": "Tener todo en un lugar le da historial para montos mayores."}]
    else:
        objections = [{"objecion": "No lo necesito ahora.",
                       "respuesta": "Se activa hoy, sin costo de apertura, y protege lo que ya construyó."},
                      {"objecion": "Ya trabajo con otro banco.",
                       "respuesta": "Tener todo en un lugar le da historial y mejores condiciones."}]
    return {"resumen": f"{client['business']} en {client['district']}. "
                       f"{'Buen historial de pago' if good else 'Historial con atrasos recientes'}.",
            "oferta": oferta, "talking_points": points[:3], "objeciones": objections,
            "siguiente_paso": ("Llevar la solicitud prellenada y agendar el desembolso."
                               if credit else "Activar el producto durante la visita.")}


def _chat_cross_sell(ctx):
    state, cid, q = ctx["state"], ctx["client_id"], ctx["question"].lower()
    recs = state["clients"][cid]["recommendations"]
    if re.search(r"ecosistema|pac[ií]fico|yape|tyba|aliad|grupo", q):
        eco = [r for r in recs if r["brand"] != "Mibanco"]
        if not eco:
            return {"reply": "No veo productos del ecosistema que calcen hoy."}
        return {"reply": "\n".join(f"• {r['brand']}: {r['product']} ({r['prob']}%). {r['why']}" for r in eco)}
    if re.search(r"otra|alternativa|opci[oó]n", q):
        r = sorted(recs, key=lambda x: -x["prob"])[1]
        return {"reply": f"Segunda opción: {r['product']} ({r['brand']}), {r['prob']}% de probabilidad. {r['why']}"}
    if re.search(r"por ?qu[eé]|raz[oó]n", q):
        lines = [f"{state['catalog'][i['product_id']]['name']}: {i['reason']}" for i in ctx["result"]["proposed"]]
        return {"reply": "\n".join(lines) or "No propuse productos para este cliente."}
    return {"reply": "Anotado como retroalimentación. Ajusto la próxima propuesta para este cliente con tu comentario."}


def _chat_risk(ctx):
    state, cid, q = ctx["state"], ctx["client_id"], ctx["question"].lower()
    client, policy = state["clients"][cid], state["policy"]
    credit = next((d for d in ctx["result"]["decisions"] if rules.is_credit(state, d["product_id"])), None)
    late_veto = client["max_days_late_12m"] > policy["max_days_late"]
    if re.search(r"15|subir|sube|m[aá]s monto", q):
        if not credit:
            return {"reply": "Esta oferta no incluye crédito, así que no hay monto que subir."}
        check = rules.check_policy(state, cid, credit["product_id"], 15000)
        if check["approved"]:
            return {"reply": "Con S/ 15,000 la oferta sigue dentro de la política."}
        return {"reply": f"No: con S/ 15,000 {check['reasons'][0]}. Si lo subes en la aprobación, se bloquea."}
    if re.search(r"mejorar|cambiar|tendr[ií]a", q):
        if late_veto:
            return {"reply": "Mantener 12 meses sin atrasos mayores a 15 días. Con eso el crédito vuelve a evaluarse."}
        return {"reply": "Reducir su deuda en otras entidades libera capacidad: cada S/ 1,000 que paga suma S/ 1,000 al máximo."}
    if re.search(r"monto|m[aá]ximo|por ?qu[eé]|capacidad", q):
        if late_veto:
            return {"reply": f"El crédito está vetado por atraso: {client['max_days_late_12m']} días en 12 meses y la política permite {policy['max_days_late']}."}
        cap = max(0, policy["debt_multiple"] * client["monthly_net_income"] - client["current_debt"])
        return {"reply": f"Capacidad = {policy['debt_multiple']} × ingreso ({rules.fmt_soles(client['monthly_net_income'])}) − "
                         f"deuda actual ({rules.fmt_soles(client['current_debt'])}) = {rules.fmt_soles(cap)}.\n"
                         f"Se redondea hacia abajo a múltiplos de S/ {policy['round_to']}. Los productos sin crédito no suman deuda."}
    return {"reply": "Anotado como retroalimentación para el modelo de riesgo. La decisión de política no cambia, pero tu comentario queda registrado."}


HANDLERS = {"cross_sell": _cross_sell, "risk": _risk, "brief": _brief,
            "chat_cross_sell": _chat_cross_sell, "chat_risk": _chat_risk}
PACE_SHARE = {"cross_sell": 0.55, "risk": 0.45}


def respond(agent, ctx):
    _pace(ctx, PACE_SHARE.get(agent, 0))
    return HANDLERS[agent](ctx)
