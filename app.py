"""Crosspilot UI (requirements_v2 §2–§6). All decisions come from crosspilot.rules."""
import datetime as dt
import html
import os
import queue

import streamlit as st

from crosspilot import agents, rules
from crosspilot.data import client_history, new_state, products_per_client, projected_products_per_client
from crosspilot.llm import AgentError
from crosspilot.orchestrator import ORQ, run_one, run_portfolio

st.set_page_config(page_title="Crosspilot", page_icon="🧭", layout="wide")

TAG_COLORS = {rules.APROBADO: "#007F73", rules.CONTRAOFERTA: "#C2410C", rules.VETO: "#7A1A12"}
STATUS_BADGES = {
    "PENDIENTE": ("Por aprobar", "#F2B134", "#0F2A2E"),
    "APROBADA": ("Aprobada", "#007F73", "#FFFFFF"),
    "RECHAZADA": ("Rechazada", "#4A6572", "#FFFFFF"),
    "SIN_OFERTA": ("Sin oferta", "#EEF2F3", "#4A6572"),
}
TABS = {"cross_sell": ("🎯", "Venta cruzada", "#EAF4F2"), "risk": ("🛡️", "Riesgo", "#FCEEE7")}
CHIPS = {
    "cross_sell": ["¿Por qué estos productos?", "¿Qué otra opción hay?", "¿Y del ecosistema?"],
    "risk": ["¿Por qué ese monto máximo?", "¿Y si subo a S/ 15,000?", "¿Qué tendría que mejorar?"],
}
DAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "setiembre",
          "octubre", "noviembre", "diciembre"]

CSS = """
<style>
html, body, [class*="css"], .stMarkdown, p, li, label { font-family: Calibri, Carlito, "Segoe UI", sans-serif; }
h1, h2, h3, .cp-serif { font-family: Cambria, Caladea, Georgia, serif !important; color: #0F2A2E; }
section[data-testid="stSidebar"] { background: #0F2A2E; }
section[data-testid="stSidebar"] * { color: #FFFFFF; }
section[data-testid="stSidebar"] [data-testid="stMetricValue"] { color: #8FD3C4; }
section[data-testid="stSidebar"] [data-testid="stMetricDelta"] * { color: #8FD3C4 !important; }
section[data-testid="stSidebar"] button { background: #0B4F57; border: 1px solid #8FD3C4; }
.cp-muted { color: #4A6572; }
.cp-chip { display: inline-block; background: #EEF2F3; color: #0F2A2E; border-radius: 6px; padding: 1px 8px;
           margin: 2px 4px 2px 0; font-size: 14px; }
.cp-tag { display: inline-block; color: #FFF; border-radius: 4px; padding: 0 6px; font-size: 11px; font-weight: 700;
          margin-left: 6px; vertical-align: middle; }
.cp-pos { display: inline-flex; width: 30px; height: 30px; border-radius: 50%; align-items: center;
          justify-content: center; font-weight: 700; }
.cp-pill { display: inline-flex; align-items: center; gap: 8px; border-radius: 999px; padding: 2px 12px 2px 4px; }
.cp-dot { width: 22px; height: 22px; border-radius: 50%; display: inline-block; }
.cp-score { font-family: Cambria, Georgia, serif; font-size: 24px; font-weight: 700; color: #0F2A2E; }
.cp-badge { display: inline-block; border-radius: 6px; padding: 2px 10px; font-size: 14px; font-weight: 700; }
.cp-head { color: #4A6572; font-size: 13px; text-transform: uppercase; font-weight: 700; letter-spacing: .03em; }
.cp-band { background: #0B4F57; color: #FFF; border-radius: 10px; padding: 12px 16px; margin-bottom: 12px; }
.cp-hero { background: #0F2A2E; color: #FFF; border-radius: 10px; padding: 18px 22px; margin-bottom: 16px; }
.cp-hero h2 { color: #FFF !important; margin: 0; font-size: 28px; }
.cp-hero .sub { color: #8FD3C4; }
.cp-error { background: #FCEEE7; border: 1px solid #C2410C; border-radius: 10px; padding: 10px 14px; color: #7A1A12; }
.cp-card { background: #EAF4F2; border-radius: 10px; padding: 14px 18px; }
.cp-bar { background: #EEF2F3; border-radius: 4px; height: 8px; }
.cp-bar > div { height: 8px; border-radius: 4px; }
[class*="st-key-ai-"] { background: #EAF4F2; border: 1px solid #B5D3CC; border-radius: 10px; padding: 10px 14px; }
[class*="st-key-manual-"] { background: #FFFFFF; border: 1px solid #D7E7E3; border-radius: 10px; padding: 10px 14px; }
.cp-grid { display: grid; align-items: center; column-gap: 16px;
           grid-template-columns: 44px minmax(150px, 1.3fr) minmax(150px, 1.2fr) minmax(250px, 2fr) 104px 112px; }
.cp-row { min-height: 64px; }
[data-testid="stHorizontalBlock"]:has(.cp-row) [data-testid="stMarkdownContainer"],
[data-testid="stHorizontalBlock"]:has(.cp-row-head) [data-testid="stMarkdownContainer"] { margin-bottom: 0; }
.cp-offer-line { display: flex; flex-wrap: wrap; align-items: center; gap: 2px 6px; line-height: 1.5; font-size: 15px; }
.cp-offer-line .cp-tag { margin-left: 0; }
[data-testid="stHorizontalBlock"]:has(.cp-row) { border-bottom: 1px solid #D7E7E3; padding: 8px 4px; }
[data-testid="stHorizontalBlock"]:has(.cp-row):hover { background: #F4FAF8; }
[data-testid="stHorizontalBlock"]:has(.cp-row-head) { background: #F4FAF8; border-radius: 8px 8px 0 0;
                                                      border-bottom: 1px solid #D7E7E3; padding: 12px 4px; }
[data-testid="stHorizontalBlock"]:has(.cp-row) .stMarkdown p,
[data-testid="stHorizontalBlock"]:has(.cp-row-head) .stMarkdown p { margin: 0; }
section[data-testid="stSidebar"] ul { margin: 0 0 8px 0; padding-left: 18px; }
section[data-testid="stSidebar"] li { font-size: 15px; margin: 0; }
</style>
"""


# ---------- session state ----------

def _secret_key():
    """Streamlit Cloud: expose the API key from Secrets to the SDK through the environment."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return True
    try:
        key = st.secrets["ANTHROPIC_API_KEY"]
    except Exception:  # no secrets file or no key: Streamlit raises different errors per version
        return False
    os.environ["ANTHROPIC_API_KEY"] = key
    return True


def init_session(reset=False):
    ss = st.session_state
    if reset or "state" not in ss:
        ss.state = new_state()
        ss.runs, ss.decisions, ss.chats, ss.detail = {}, {}, {}, None
        ss.auto_started = False
    if "fallback" not in ss:
        ss.fallback = os.environ.get("CROSSPILOT_FAKE_LLM") == "1" or not _secret_key()


def fake_mode():
    return bool(st.session_state.fallback)


def store_run(cid, run):
    ss = st.session_state
    ss.runs[cid] = run
    if run["status"] != "done":
        return
    res = run["result"]
    ss.decisions[cid] = {
        "status": "PENDIENTE" if res["items"] else "SIN_OFERTA",
        "list": [i["product_id"] for i in res["items"]],
        "amounts": {i["product_id"]: i["amount"] for i in res["items"]},
        "limited": False, "errors": [], "comment": "", "approved": None, "brief": None, "brief_error": None,
    }
    proposed = "\n".join([f"“{res['pitch']}”"] + [
        f"• {name(i['product_id'])}{amount_text(i.get('amount'))}: {i.get('reason', '')}" for i in res["proposed"]])
    risk = "\n".join(f"{d['decision']} · {name(d['product_id'])}: {d['explanation']}" for d in res["decisions"])
    ss.chats[cid] = {"cross_sell": [{"role": "agent", "text": proposed}],
                     "risk": [{"role": "agent", "text": risk or "No hay productos nuevos que evaluar."}]}


# ---------- formatting helpers ----------

def esc(text):
    return html.escape(str(text))


def name(pid, short=False):
    product = st.session_state.state["catalog"][pid]
    return product["short"] if short else product["name"]


def amount_text(amount):
    return f" por {rules.fmt_soles(amount)}" if amount is not None else ""


def light(score):
    if score > 80:
        return "#1E9E5A", "#E3F4EA"
    if score >= 60:
        return "#F2B134", "#FDF1D6"
    return "#C62828", "#FBE4E4"


def today_label():
    today = dt.date.fromisoformat(st.session_state.state["meta"]["today"])
    return f"{DAYS[today.weekday()]} {today.day} de {MONTHS[today.month - 1]}"


def scored_rows():
    """Analyzed clients by priority desc, then the rest (V2.5)."""
    ss = st.session_state
    rows = []
    for cid in ss.state["clients"]:
        run = ss.runs.get(cid, {"status": "idle"})
        score = rules.priority_score(ss.state, cid, run["result"]) if run["status"] == "done" else None
        rows.append({"cid": cid, "run": run, "score": score})
    rows.sort(key=lambda r: (r["score"] is None, -(r["score"] or 0), r["cid"]))
    return rows


# ---------- sidebar ----------

def sidebar():
    ss = st.session_state
    state = ss.state
    approved = [d for d in ss.decisions.values() if d["status"] == "APROBADA"]
    approved_items = sum(len(d["approved"]) for d in approved)
    vetoes = sum(r["result"]["vetoes"] for r in ss.runs.values() if r["status"] == "done")
    state["stats"].update(approved_offers=len(approved), vetoes=vetoes)
    now, projected = products_per_client(state), projected_products_per_client(state, approved_items)
    with st.sidebar:
        st.markdown("<h2 style='color:#FFF;margin-bottom:0'>Crosspilot</h2>"
                    "<div style='color:#8FD3C4;margin-bottom:12px'>Copiloto de priorización y pre-visita</div>", unsafe_allow_html=True)
        st.toggle("Modo respaldo", key="fallback")
        st.caption("Respuestas predefinidas, sin llamar a la API.")
        st.metric("Productos por cliente", f"{now:.1f}",
                  delta=f"{projected:.1f} si aceptan lo aprobado" if projected > now else None)
        done = sum(r["status"] == "done" for r in ss.runs.values())
        st.metric("Clientes analizados", f"{done}/{len(state['clients'])}")
        c1, c2 = st.columns(2)
        c1.metric("Ofertas aprobadas", len(approved))
        c2.metric("Vetos de riesgo", vetoes)
        if st.button("Reiniciar demo", use_container_width=True):
            init_session(reset=True)
            st.rerun()
        st.markdown("---\n**Productos para ofrecer**")
        bank = rules.bank_products(state)
        allies = [pid for pid, p in state["catalog"].items() if p["type"] == "aliado"]
        st.markdown("Del banco\n" + "\n".join(f"- {name(p)}" for p in bank))
        st.markdown("De aliados\n" + "\n".join(
            f"- {name(p)} · {state['catalog'][p]['brand']}" for p in allies))
        st.caption("Aliados de ejemplo, sin acuerdo comercial.")
        st.caption("Próximo módulo: registro post-visita (en evolución).")


# ---------- portfolio table ----------

ROW_SPLIT = [11, 0.9]  # grid with the data | action button
HEADERS = ["Orden", "Cliente", "Productos actuales", "Oferta tras riesgo", "Prioridad", "Estado"]


def offer_cell(run, stage):
    if run["status"] == "error":
        return f"<span style='color:#C2410C;font-weight:700'>⚠ {esc(run['error'])}</span>"
    if run["status"] != "done":
        if stage in (None, "queued"):
            return "<span class='cp-muted'>En cola</span>"
        vc = "✓" if stage == "risk" else "⏳"
        risk = "⏳" if stage == "risk" else "·"
        return f"<span class='cp-muted'>Venta cruzada {vc} &nbsp; Riesgo {risk}</span>"
    res = run["result"]
    if not res["decisions"]:
        return "<span class='cp-muted'>Sin oferta viable</span>"
    lines = []
    for d in res["decisions"]:
        amount = d["max_amount"] if d["decision"] == rules.CONTRAOFERTA else d.get("amount")
        label = name(d["product_id"], short=True) + (f" {rules.fmt_soles(amount)}" if amount is not None else "")
        lines.append(f"<div class='cp-offer-line'><b>{esc(label)}</b><span class='cp-tag' "
                     f"style='background:{TAG_COLORS[d['decision']]}'>{d['decision']}</span></div>")
    return "".join(lines)


def row_html(pos, row, stage):
    """One CSS-grid row, so every cell shares the same height and column widths."""
    ss = st.session_state
    cid, run, score = row["cid"], row["run"], row["score"]
    client = ss.state["clients"][cid]
    top = score is not None and pos <= 3
    position = (f"<span class='cp-pos' style='background:{'#0B4F57' if top else '#EEF2F3'};"
                f"color:{'#FFF' if top else '#4A6572'}'>{pos}</span>")
    who = f"<div><b>{esc(client['name'])}</b><br><span class='cp-muted'>{esc(client['business'])}</span></div>"
    chips = "<div>" + "".join(f"<span class='cp-chip'>{esc(name(p, short=True))}</span>" for p in client["products"]) + "</div>"
    if score is None:
        priority = "<span class='cp-muted'>—</span>"
    else:
        dot, bg = light(score)
        priority = (f"<span class='cp-pill' style='background:{bg}'><span class='cp-dot' style='background:{dot}'>"
                    f"</span><span class='cp-score'>{score}</span></span>")
    decision = ss.decisions.get(cid)
    status = ""
    if decision:
        label, bg, fg = STATUS_BADGES[decision["status"]]
        status = f"<span class='cp-badge' style='background:{bg};color:{fg}'>{label}</span>"
    cells = [position, who, chips, f"<div>{offer_cell(run, stage)}</div>", priority, status]
    return "<div class='cp-grid cp-row'>" + "".join(f"<div>{c}</div>" for c in cells) + "</div>"


def render_row(pos, row, stage=None, interactive=True):
    ss = st.session_state
    cid, run = row["cid"], row["run"]
    data, action = st.columns(ROW_SPLIT, vertical_alignment="center")
    data.markdown(row_html(pos, row, stage), unsafe_allow_html=True)
    if not interactive:
        return
    if run["status"] == "error":
        if action.button("Reintentar", key=f"retry-{cid}", use_container_width=True):
            with st.spinner(f"Reintentando {ss.state['clients'][cid]['name']}…"):
                store_run(cid, run_one(ss.state, cid, fake=fake_mode()))
            st.rerun()
    elif run["status"] == "done" and action.button("Ver", key=f"open-{cid}", type="primary",
                                                   use_container_width=True):
        ss.detail = cid
        st.rerun()


def table_header():
    data, _ = st.columns(ROW_SPLIT, vertical_alignment="bottom")
    data.markdown("<div class='cp-grid cp-row-head'>" + "".join(f"<div class='cp-head'>{t}</div>" for t in HEADERS)
                  + "</div>", unsafe_allow_html=True)


def analyze(progress_slot, table_slot):
    """Runs every client in parallel and repaints the table while agents work (V1.1–V1.3)."""
    ss = st.session_state
    cids = list(ss.state["clients"])
    ss.runs, ss.decisions, ss.chats = {}, {}, {}
    events, stages = queue.Queue(), {cid: "queued" for cid in cids}

    def on_stage(cid, stage):  # worker thread: only touch the queue
        events.put((cid, stage))

    def on_done(cid, run):
        stages[cid] = "done"
        store_run(cid, run)

    def paint():
        while not events.empty():
            cid, stage = events.get()
            if stages[cid] != "done":
                stages[cid] = stage
        done = len(ss.runs)
        progress_slot.progress(done / len(cids), text=f"Agentes analizando en paralelo · {done}/{len(cids)}")
        with table_slot.container():
            table_header()
            for pos, row in enumerate(scored_rows(), start=1):
                render_row(pos, row, stages[row["cid"]], interactive=False)

    paint()
    run_portfolio(ss.state, cids, fake=fake_mode(), on_stage=on_stage, on_done=on_done, on_tick=paint,
                  pace=1.0 if fake_mode() else 0)


def portfolio_page():
    ss = st.session_state
    n = len(ss.state["clients"])
    head, action = st.columns([4, 1.3], vertical_alignment="bottom")
    head.markdown(f"<div class='cp-muted' style='font-size:16px'>{today_label()} · {n} clientes agendados</div>",
                  unsafe_allow_html=True)
    head.title("Cartera priorizada del día")
    head.markdown("<span class='cp-muted'>Prioridad de visita: probabilidad de que el cliente adquiera más productos, "
                  "con la oferta ya validada por Riesgo.</span>", unsafe_allow_html=True)
    clicked = action.button("Analizar cartera", type="primary", use_container_width=True)
    progress_slot, table_slot = st.empty(), st.empty()
    if clicked or not ss.auto_started:
        ss.auto_started = True
        analyze(progress_slot, table_slot)
        st.rerun()
    done = sum(r["status"] == "done" for r in ss.runs.values())
    errors = sum(r["status"] == "error" for r in ss.runs.values())
    text = f"{n} clientes analizados en paralelo" if done == n else f"{done}/{n} analizados"
    progress_slot.progress(done / n, text=text)
    if errors:
        st.warning(f"{errors} cliente(s) con error. Pulsa Reintentar"
                   + ("." if fake_mode() else " o activa el Modo respaldo."))
    with table_slot.container():
        table_header()
        for pos, row in enumerate(scored_rows(), start=1):
            render_row(pos, row)
    st.caption("El puntaje es un apoyo, no una decisión: el ejecutivo valida en terreno y aprueba cada oferta.")


# ---------- detail page ----------

@st.dialog("Agregar producto", width="large")
def add_product_dialog(cid):
    ss = st.session_state
    state, decision = ss.state, ss.decisions[cid]
    client = state["clients"][cid]
    credit_blocked = decision["limited"] or decision["status"] == "SIN_OFERTA"
    if credit_blocked:
        st.info("Sin oferta viable de crédito: solo puedes agregar productos sin crédito.")
    bank_col, ally_col = st.columns(2)
    bank_col.markdown("<span class='cp-head'>Del banco</span>", unsafe_allow_html=True)
    ally_col.markdown("<span class='cp-head'>De aliados</span>", unsafe_allow_html=True)

    def add(pid):
        if decision["status"] == "SIN_OFERTA":
            decision.update(status="PENDIENTE", limited=True)
        check = rules.check_policy(state, cid, pid)
        decision["list"].append(pid)
        decision["amounts"][pid] = (check["max_amount"] or state["catalog"][pid]["min_amount"]) \
            if rules.is_credit(state, pid) else None
        decision["errors"] = []
        st.rerun()

    for pid in rules.bank_products(state):
        check = rules.check_policy(state, cid, pid)
        credit = rules.is_credit(state, pid)
        eligible = rules.decide(state, pid, check) != rules.VETO
        note = ("No elegible hoy" if credit and (credit_blocked or not eligible) else
                f"Hasta {rules.fmt_soles(check['max_amount'])}" if credit else "Sin crédito")
        row = bank_col.columns([3, 1.4], vertical_alignment="center")
        row[0].markdown(f"**{name(pid)}**  \n<span class='cp-muted'>{note}</span>", unsafe_allow_html=True)
        if pid in client["products"]:
            row[1].caption("Ya lo tiene")
        elif pid in decision["list"]:
            row[1].caption("En la oferta")
        elif not (credit and (credit_blocked or not eligible)) and row[1].button("+ Agregar", key=f"add-{cid}-{pid}"):
            add(pid)
    for pid, product in state["catalog"].items():
        if product["type"] != "aliado":
            continue
        rec = next((r for r in client["recommendations"] if r["brand"] == product["brand"]), None)
        row = ally_col.columns([3, 1.4], vertical_alignment="center")
        affinity = f" · Afinidad {rec['prob']}%" if rec else ""
        row[0].markdown(f"**{name(pid)}**  \n<span class='cp-muted'>{product['brand']}{affinity}</span>",
                        unsafe_allow_html=True)
        if pid in decision["list"]:
            row[1].caption("En la oferta")
        elif row[1].button("+ Agregar", key=f"add-{cid}-{pid}"):
            add(pid)
    st.caption("Aliados de ejemplo, sin acuerdo comercial.")


def offer_items(cid, res, decision):
    state = st.session_state.state
    ai = {i["product_id"]: i for i in res["items"]}
    for pid in list(decision["list"]):
        is_ai, credit = pid in ai, rules.is_credit(state, pid)
        product = state["catalog"][pid]
        with st.container(key=f"{'ai' if is_ai else 'manual'}-{cid}-{pid}"):
            left, mid, right = st.columns([3, 2, 0.6], vertical_alignment="center")
            if is_ai:
                item = ai[pid]
                tag = ("<span style='color:#C2410C'>Contraoferta de Riesgo · propuesto "
                       f"{rules.fmt_soles(item['proposed_amount'])}</span>" if item["decision"] == rules.CONTRAOFERTA
                       else "<span style='color:#007F73'>Aprobado por Riesgo</span>")
                badge = "<span class='cp-tag' style='background:#0B4F57'>RECOMENDADO POR IA</span>"
            else:
                tag = ("Agregado por ti · Riesgo lo valida al aprobar" if credit else
                       f"Agregado por ti · Aliado {product['brand']}" if product["type"] == "aliado" else "Agregado por ti")
                tag, badge = f"<span class='cp-muted'>{tag}</span>", ""
            left.markdown(f"**{esc(product['name'])}**{badge}<br><small>{tag}</small>", unsafe_allow_html=True)
            if credit:
                max_amount = rules.check_policy(state, cid, pid)["max_amount"] or 0
                amount = mid.number_input("Monto (S/)", min_value=0, step=500, value=int(decision["amounts"][pid] or 0),
                                          key=f"amt-{cid}-{pid}")
                decision["amounts"][pid] = int(amount)
                over = amount > max_amount
                mid.markdown(f"<small style='color:{'#C2410C' if over else '#4A6572'}'>"
                             f"{'Supera el máximo' if over else 'Máximo permitido'}: {rules.fmt_soles(max_amount)}</small>",
                             unsafe_allow_html=True)
            if right.button("🗑", key=f"rm-{cid}-{pid}", help="Quitar de la oferta"):
                decision["list"].remove(pid)
                decision["errors"] = []
                st.rerun()


def approve(cid, decision, res):
    ss = st.session_state
    state = ss.state
    items = [{"product_id": pid, "amount": decision["amounts"][pid] if rules.is_credit(state, pid) else None}
             for pid in decision["list"]]
    decision["errors"] = rules.validate_approval(state, cid, items)
    if decision["errors"]:
        return
    decision.update(status="APROBADA", approved=items)
    make_brief(cid, decision, res)


def make_brief(cid, decision, res):
    with st.spinner("El agente Visita está preparando la ficha…"):
        try:
            decision["brief"] = agents.visit_brief(st.session_state.state, cid, decision["approved"], res["pitch"],
                                                   fake=fake_mode())
            decision["brief_error"] = None
        except AgentError as exc:
            decision["brief_error"] = f"{exc}. Activa el Modo respaldo y vuelve a intentar."


def offer_section(cid):
    ss = st.session_state
    res, decision = ss.runs[cid]["result"], ss.decisions[cid]
    st.subheader("Oferta")
    st.markdown(f"<div class='cp-band'>🧭 <b>{ORQ}</b> · {esc(res['closing'])}</div>", unsafe_allow_html=True)
    status = decision["status"]
    if status in ("PENDIENTE", "SIN_OFERTA"):
        if status == "SIN_OFERTA":
            st.info("Sin oferta viable. Puedes agregar productos sin crédito (ahorro, seguros, QR, aliados).")
        offer_items(cid, res, decision)
        if st.button("+ Agregar producto", key=f"open-add-{cid}"):
            add_product_dialog(cid)
        decision["comment"] = st.text_area("Comentarios", value=decision["comment"], key=f"comment-{cid}",
                                           placeholder="Contexto para el análisis posterior (opcional)")
        if decision["errors"]:
            st.markdown("<div class='cp-error'><b>No se puede aprobar</b><br>"
                        + "<br>".join(esc(e) for e in decision["errors"]) + "</div>", unsafe_allow_html=True)
        if status == "PENDIENTE":
            a, r, _ = st.columns([1, 1, 2])
            if a.button("Aprobar", type="primary", key=f"approve-{cid}", use_container_width=True):
                approve(cid, decision, res)
                st.rerun()
            if r.button("Rechazar", key=f"reject-{cid}", use_container_width=True):
                decision.update(status="RECHAZADA", errors=[])
                st.rerun()
        return
    label, bg, fg = STATUS_BADGES[status]
    st.markdown(f"<span class='cp-badge' style='background:{bg};color:{fg}'>{label}</span>", unsafe_allow_html=True)
    if decision["approved"]:
        st.markdown("\n".join(f"- {name(i['product_id'])}{amount_text(i['amount'])}" for i in decision["approved"]))
    if decision["comment"]:
        st.caption(f"Comentario: {decision['comment']}")


def brief_section(cid):
    ss = st.session_state
    decision, res = ss.decisions[cid], ss.runs[cid]["result"]
    if decision["status"] != "APROBADA":
        return
    st.subheader("Ficha de visita")
    if decision["brief_error"]:
        st.error(decision["brief_error"])
        if st.button("Reintentar ficha", key=f"brief-retry-{cid}"):
            make_brief(cid, decision, res)
            st.rerun()
        return
    brief = decision["brief"]
    if not brief:
        return
    # R6.2: the offer comes from the approved items, never from the agent's text.
    offer = "<br>".join(esc(name(i["product_id"]) + amount_text(i["amount"])) for i in decision["approved"])
    points = "".join(f"<li>{esc(t)}</li>" for t in brief["talking_points"])
    objections = "".join(f"<li><b>{esc(o['objecion'])}</b><br>{esc(o['respuesta'])}</li>" for o in brief["objeciones"])
    st.markdown(f"""<div class='cp-card'>
<p>{esc(brief['resumen'])}</p>
<p><b>Oferta aprobada</b><br>{offer}</p>
<p><b>Puntos de conversación</b></p><ol>{points}</ol>
<p><b>Objeciones probables</b></p><ul>{objections}</ul>
<p><b>Siguiente paso:</b> {esc(brief['siguiente_paso'])}</p></div>""", unsafe_allow_html=True)


def chat_section(cid):
    ss = st.session_state
    res = ss.runs[cid]["result"]
    st.subheader("Conversa con los agentes")
    tabs = st.tabs([f"{icon} {label}" for icon, label, _ in TABS.values()])
    for tab_key, tab in zip(TABS, tabs):
        icon = TABS[tab_key][0]
        with tab:
            history = ss.chats[cid][tab_key]
            with st.container(height=340):
                for msg in history:
                    with st.chat_message("user" if msg["role"] == "user" else "assistant",
                                         avatar="👤" if msg["role"] == "user" else icon):
                        st.markdown(esc(msg["text"]).replace("\n", "  \n"))
            chips = st.columns(3)
            question = None
            for chip, text in zip(chips, CHIPS[tab_key]):
                if chip.button(text, key=f"chip-{cid}-{tab_key}-{text}", use_container_width=True):
                    question = text
            typed = st.chat_input(f"Pregunta o corrige a {TABS[tab_key][1]}", key=f"input-{cid}-{tab_key}")
            question = question or typed
            if question:
                past = [{"role": m["role"], "text": m["text"]} for m in history]
                history.append({"role": "user", "text": question})
                with st.spinner(f"{TABS[tab_key][1]} está respondiendo…"):
                    try:
                        reply = agents.chat_reply(ss.state, cid, tab_key, question, past, res, fake=fake_mode())
                    except AgentError as exc:
                        reply = f"{exc}. Activa el Modo respaldo y vuelve a intentar."
                history.append({"role": "agent", "text": reply})
                st.rerun()


def profile_section(cid):
    state = st.session_state.state
    client = state["clients"][cid]
    year = state["meta"]["reference_year"]
    late = client["max_days_late_12m"]
    sbs, sbs_bg = ("Normal", "#007F73") if late <= 8 else ("CPP", "#F2B134") if late <= 30 else ("Deficiente", "#C2410C")
    st.subheader("Perfil del cliente")
    m = st.columns(5)
    m[0].metric("Años en el banco", year - client["bank_since"], help=f"Desde {client['bank_since']}")
    m[1].metric("Años en el sistema", year - client["system_since"], help=f"Desde {client['system_since']}")
    m[2].metric("Principalidad", f"{round(client['principality'] * 100)}%")
    m[3].metric("Mora máx. 12m", f"{late} días")
    m[4].markdown(f"<div class='cp-muted'>Calificación SBS</div><span class='cp-badge' "
                  f"style='background:{sbs_bg};color:#FFF;font-size:20px'>{sbs}</span>", unsafe_allow_html=True)

    hist = client_history(state, cid)
    left, right = st.columns(2)
    with left:
        st.markdown("**Deuda 24 meses (S/)**: banco vs otras entidades")
        if client["current_debt"]:
            st.bar_chart({"Mes": hist["months"], "Banco": hist["debt_bank"], "Otras": hist["debt_other"]},
                         x="Mes", y=["Banco", "Otras"], color=["#007F73", "#B5C7CE"], height=220)
        else:
            st.caption("Sin deuda en el sistema financiero.")
        st.markdown("**Atraso por mes (días)**")
        st.bar_chart({"Mes": hist["late_months"], "Días": hist["late_days"]}, x="Mes", y="Días",
                     color="#C2410C", height=160)
    with right:
        st.markdown("**Ahorro 24 meses (S/)**")
        if hist["savings"]:
            st.line_chart({"Mes": hist["months"], "Ahorro": hist["savings"]}, x="Mes", y="Ahorro",
                          color="#007F73", height=220)
        else:
            st.caption("No tiene ahorro con el banco.")
        st.markdown("**Productos del banco**")
        eligible = rules.eligible_products(state, cid)
        for pid in rules.bank_products(state):
            if pid in client["products"]:
                since = client["product_since"].get(pid, "").replace("-", "/")
                st.markdown(f"✅ {name(pid)} <span class='cp-muted'>· desde {since}</span>", unsafe_allow_html=True)
            elif pid in eligible:
                st.markdown(f"➕ {name(pid)} <span style='color:#007F73'>· elegible</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"⛔ {name(pid)} <span class='cp-muted'>· no elegible hoy</span>", unsafe_allow_html=True)

    left, right = st.columns(2)
    with left:
        st.markdown("**Línea de tiempo**")
        events = [(str(client["system_since"]), "Primer producto en el sistema financiero")]
        if client["bank_since"] != client["system_since"]:
            events.append((str(client["bank_since"]), "Ingresa al banco"))
        else:
            events[0] = (str(client["system_since"]), "Ingresa al sistema financiero con el banco")
        for pid, since in sorted(client["product_since"].items(), key=lambda kv: kv[1]):
            events.append((since.replace("-", "/"), f"Contrata {name(pid).lower()}"))
        st.markdown("\n".join(f"- **{d}** · {t}" for d, t in events))
        st.markdown("**Intereses**")
        st.markdown("".join(f"<span class='cp-chip'>{esc(i)}</span>" for i in client["interests"]), unsafe_allow_html=True)
    with right:
        st.markdown("**Productos con alta probabilidad** (banco y ecosistema)")
        for rec in sorted(client["recommendations"], key=lambda r: -r["prob"]):
            color = "#007F73" if rec["prob"] >= 75 else "#F2B134" if rec["prob"] >= 60 else "#B5C7CE"
            st.markdown(f"<b>{esc(rec['product'])}</b> <span class='cp-muted'>· {esc(rec['brand'])} · {rec['prob']}%</span>"
                        f"<div class='cp-bar'><div style='width:{rec['prob']}%;background:{color}'></div></div>"
                        f"<small class='cp-muted'>{esc(rec['why'])}</small>", unsafe_allow_html=True)


def detail_page(cid):
    ss = st.session_state
    client = ss.state["clients"][cid]
    if st.button("← Volver a la cartera"):
        ss.detail = None
        st.rerun()
    rows = scored_rows()
    pos = next(i for i, r in enumerate(rows, start=1) if r["cid"] == cid)
    score = rows[pos - 1]["score"]
    st.markdown(f"""<div class='cp-hero'><h2>{esc(client['name'])}</h2>
<div class='sub'>{cid} · {esc(client['business'])} · {esc(client['district'])} · Ingreso neto
{rules.fmt_soles(client['monthly_net_income'])}/mes &nbsp;
<span class='cp-badge' style='background:#8FD3C4;color:#0F2A2E'>Prioridad {score} · #{pos}</span></div></div>""",
                unsafe_allow_html=True)
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        offer_section(cid)
        brief_section(cid)
    with right:
        chat_section(cid)
    st.divider()
    profile_section(cid)


def main():
    init_session()
    st.markdown(CSS, unsafe_allow_html=True)
    sidebar()
    ss = st.session_state
    if ss.detail and ss.runs.get(ss.detail, {}).get("status") == "done":
        detail_page(ss.detail)
    else:
        ss.detail = None
        portfolio_page()


main()
