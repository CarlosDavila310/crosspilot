"""LLM agents: prompts, tools and calls (design §7). They write text; rules.py decides."""
import json

from crosspilot import rules
from crosspilot.llm import run_agent

CROSS_SELL_SYSTEM = (
    "Eres el agente Venta cruzada de Crosspilot, el copiloto de un ejecutivo de negocios de un banco de "
    "microfinanzas en Perú. Tu trabajo es proponer el siguiente producto para un cliente que ya es del banco. "
    "Reglas: propón 1 o 2 productos del catálogo que el cliente no tenga; como máximo uno de crédito. Para "
    "créditos indica el monto en soles que el negocio necesita según sus señales; para los demás, amount es "
    "null. Justifica cada producto con una señal concreta del cliente. No evalúes riesgo: otro agente lo hace. "
    "Responde siempre llamando a submit_offer, en español y con frases cortas."
)

RISK_SYSTEM = (
    "Eres el agente Riesgo de Crosspilot. Revisa la oferta para el cliente. Para cada producto llama a "
    "check_policy con su monto. El resultado de check_policy es definitivo: no puedes cambiarlo. Luego llama a "
    "submit_risk_review con una explicación de máximo 25 palabras por producto, clara para el ejecutivo. Si hay "
    "un monto máximo menor al propuesto, menciónalo y di qué regla lo limita. Cuida que la venta sea sana para "
    "el cliente."
)

BRIEF_SYSTEM = (
    "Eres el agente Visita de Crosspilot. Con el cliente y la oferta aprobada, escribe una ficha que el "
    "ejecutivo lea en un minuto antes de la visita: resumen del cliente en dos líneas, la oferta tal cual está "
    "aprobada, 3 puntos de conversación basados en las señales del cliente, 2 objeciones probables con su "
    "respuesta y el siguiente paso. No cambies productos ni montos. Llama a submit_brief."
)

CHAT_CROSS_SELL_SYSTEM = (
    "Eres el agente Venta cruzada de Crosspilot. Ya propusiste una oferta para este cliente y el ejecutivo te "
    "hace una pregunta o una corrección. Responde en español, en máximo 60 palabras, con datos del cliente, su "
    "perfil y sus recomendaciones (banco y aliados del ecosistema). No prometas montos: Riesgo los decide. Si "
    "es una corrección, agradécela y di cómo ajustarías la próxima propuesta. Llama a submit_reply."
)

CHAT_RISK_SYSTEM = (
    "Eres el agente Riesgo de Crosspilot. El ejecutivo pregunta o corrige sobre la revisión de riesgo de este "
    "cliente. Si pregunta por otro monto, llama a check_policy: su resultado es definitivo y tu respuesta nunca "
    "cambia una decisión de la política. Explica la regla (deuda total ≤ 6 × ingreso neto mensual, máximo 15 "
    "días de atraso en 12 meses, montos redondeados a S/ 500). Responde en español, en máximo 60 palabras. "
    "Llama a submit_reply."
)

CHECK_POLICY_TOOL = {
    "name": "check_policy",
    "description": "Evalúa un producto contra la política de riesgo. Su resultado es definitivo.",
    "input_schema": {
        "type": "object",
        "properties": {
            "client_id": {"type": "string"},
            "product_id": {"type": "string"},
            "amount": {"type": ["integer", "null"]},
        },
        "required": ["client_id", "product_id", "amount"],
    },
}

RISK_TOOL = {
    "name": "submit_risk_review",
    "description": "Envía la explicación de riesgo por producto.",
    "input_schema": {
        "type": "object",
        "properties": {
            "explanations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string"},
                        "explanation": {"type": "string", "description": "Máximo 25 palabras."},
                    },
                    "required": ["product_id", "explanation"],
                },
            }
        },
        "required": ["explanations"],
    },
}

BRIEF_TOOL = {
    "name": "submit_brief",
    "description": "Envía la ficha de visita.",
    "input_schema": {
        "type": "object",
        "properties": {
            "resumen": {"type": "string"},
            "oferta": {"type": "array", "items": {"type": "string"}},
            "talking_points": {"type": "array", "minItems": 3, "maxItems": 3, "items": {"type": "string"}},
            "objeciones": {
                "type": "array", "minItems": 2, "maxItems": 2,
                "items": {"type": "object",
                          "properties": {"objecion": {"type": "string"}, "respuesta": {"type": "string"}},
                          "required": ["objecion", "respuesta"]},
            },
            "siguiente_paso": {"type": "string"},
        },
        "required": ["resumen", "oferta", "talking_points", "objeciones", "siguiente_paso"],
    },
}

REPLY_TOOL = {
    "name": "submit_reply",
    "description": "Envía la respuesta al ejecutivo.",
    "input_schema": {
        "type": "object",
        "properties": {"reply": {"type": "string"}},
        "required": ["reply"],
    },
}

RISK_FIELDS = ("monthly_net_income", "current_debt", "max_days_late_12m")


def _offer_tool(state):
    return {
        "name": "submit_offer",
        "description": "Envía la propuesta de venta cruzada.",
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array", "minItems": 1, "maxItems": 2,
                    "items": {
                        "type": "object",
                        "properties": {
                            "product_id": {"type": "string", "enum": rules.bank_products(state)},
                            "amount": {"type": ["integer", "null"], "description": "Soles. Solo créditos."},
                            "reason": {"type": "string", "description": "Señal del cliente que lo justifica."},
                        },
                        "required": ["product_id", "amount", "reason"],
                    },
                },
                "pitch": {"type": "string", "description": "Una frase para el ejecutivo."},
            },
            "required": ["items", "pitch"],
        },
    }


def _json(data):
    return json.dumps(data, ensure_ascii=False)


def _catalog(state, pids):
    return {pid: {k: v for k, v in state["catalog"][pid].items() if k != "annual_margin"} for pid in pids}


def _policy_handler(state):
    return {"check_policy": lambda client_id, product_id, amount=None: rules.check_policy(state, client_id, product_id, amount)}


def cross_sell(state, client_id, fake=False, pace=0):
    client = state["clients"][client_id]
    public = {k: v for k, v in client.items() if k not in RISK_FIELDS}
    user = _json({"client_id": client_id, "cliente": public, "productos_actuales": client["products"],
                  "catalogo": _catalog(state, rules.bank_products(state))})
    return run_agent("cross_sell", CROSS_SELL_SYSTEM, user, [_offer_tool(state)], "submit_offer", fake=fake,
                     fake_ctx={"state": state, "client_id": client_id, "pace": pace})


def risk_review(state, client_id, items, fake=False, pace=0):
    user = _json({"client_id": client_id, "cliente": state["clients"][client_id], "oferta": items})
    return run_agent("risk", RISK_SYSTEM, user, [CHECK_POLICY_TOOL, RISK_TOOL], "submit_risk_review",
                     handlers=_policy_handler(state), fake=fake,
                     fake_ctx={"state": state, "client_id": client_id, "items": items, "pace": pace})


def visit_brief(state, client_id, items, pitch, fake=False):
    offer = [{"producto": state["catalog"][i["product_id"]]["name"], "monto": i.get("amount")} for i in items]
    user = _json({"cliente": state["clients"][client_id], "oferta_aprobada": offer, "pitch": pitch})
    return run_agent("brief", BRIEF_SYSTEM, user, [BRIEF_TOOL], "submit_brief", fake=fake,
                     fake_ctx={"state": state, "client_id": client_id, "items": items})


def chat_reply(state, client_id, tab, question, history, result, fake=False):
    """Follow-up chat. `tab` is "cross_sell" or "risk"; history is [{"role", "text"}]."""
    agent = f"chat_{tab}"
    user = _json({"client_id": client_id, "cliente": state["clients"][client_id],
                  "propuesta": result.get("proposed"), "revision_riesgo": result.get("decisions"),
                  "historial": history, "pregunta": question})
    system = CHAT_RISK_SYSTEM if tab == "risk" else CHAT_CROSS_SELL_SYSTEM
    tools = [CHECK_POLICY_TOOL, REPLY_TOOL] if tab == "risk" else [REPLY_TOOL]
    handlers = _policy_handler(state) if tab == "risk" else None
    out = run_agent(agent, system, user, tools, "submit_reply", handlers=handlers, fake=fake,
                    fake_ctx={"state": state, "client_id": client_id, "question": question, "result": result})
    return out["reply"]
