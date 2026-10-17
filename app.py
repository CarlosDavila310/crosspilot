"""Crosspilot UI (requirements_v2 §2–§6), recreating design/Crosspilot v2.dc.html.

All decisions come from crosspilot.rules; this file only renders and collects input.
"""
import datetime as dt
import html
import os
import queue

import streamlit as st

from crosspilot import agents, rules
from crosspilot.data import client_history, new_state, products_per_client, projected_products_per_client
from crosspilot.llm import AgentError
from crosspilot.orchestrator import run_one, run_portfolio

st.set_page_config(page_title="Crosspilot", page_icon="🧭", layout="wide")

TAG_COLORS = {rules.APROBADO: "#007F73", rules.CONTRAOFERTA: "#C2410C", rules.VETO: "#7A1A12"}
STATUS_BADGES = {
    "PENDIENTE": ("Por aprobar", "#F2B134", "#0F2A2E"),
    "APROBADA": ("Aprobada", "#007F73", "#FFFFFF"),
    "RECHAZADA": ("Rechazada", "#4A6572", "#FFFFFF"),
    "SIN_OFERTA": ("Sin oferta", "#EEF2F3", "#4A6572"),
}
TABS = {"cross_sell": (":material/target:", "Venta cruzada", "#EAF4F2"),
        "risk": (":material/shield:", "Riesgo", "#FCEEE7")}
CHIPS = {
    "cross_sell": ["¿Por qué estos productos?", "¿Qué otra opción hay?", "¿Y del ecosistema?"],
    "risk": ["¿Por qué ese monto máximo?", "¿Y si subo a S/ 15,000?", "¿Qué tendría que mejorar?"],
}
HEADERS = ["Orden", "Cliente", "Productos actuales", "Oferta de venta cruzada tras riesgo", "Prioridad de visita",
           "Estado"]
BANK_BRAND = "Mibanco"
DAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "setiembre",
          "octubre", "noviembre", "diciembre"]

# Design tokens and components from design/README.md. Streamlit widgets are styled through their `st-key-*` class.
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Caladea:wght@400;700&family=Carlito:wght@400;700&display=swap');
:root { --dark:#0F2A2E; --deep:#0B4F57; --teal:#007F73; --mint:#8FD3C4; --card:#EAF4F2; --amber:#F2B134;
        --amber-l:#FDF1D6; --risk:#C2410C; --risk-l:#FCEEE7; --veto:#7A1A12; --slate:#4A6572; --line:#D7E7E3;
        --line2:#B5D3CC; --neutral:#EEF2F3; --serif:Cambria, Caladea, Georgia, serif;
        --sans:Calibri, Carlito, "Segoe UI", sans-serif; }
html, body, .stApp, .stMarkdown, p, li, label, input, textarea, button { font-family: var(--sans); }
.stApp { color: var(--dark); background: #FFFFFF; }
.stMarkdown p { margin-bottom: 0; }
.block-container { max-width: 1320px; padding-top: 3.6rem; padding-bottom: 4rem; }
.serif { font-family: var(--serif); font-weight: 700; }
.muted { color: var(--slate); }

/* ---------- sidebar ---------- */
section[data-testid="stSidebar"] { background: var(--dark); width: 300px !important; }
section[data-testid="stSidebar"] > div { padding-top: .5rem; }
section[data-testid="stSidebar"] * { color: #FFFFFF; }
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 20px; }
.sb-brand { display: flex; align-items: center; gap: 12px; }
.sb-logo { width: 46px; height: 46px; border-radius: 50%; background: var(--teal); display: flex;
           align-items: center; justify-content: center; font-size: 22px; flex: none; }
.sb-title { font-family: var(--serif); font-size: 30px; font-weight: 700; line-height: 1; }
.sb-sub { color: var(--mint) !important; font-size: 16px; margin-top: 4px; }
.st-key-fallback-card { background: rgba(255,255,255,.07); border-radius: 10px; padding: 14px 16px; gap: 0 !important; }
.st-key-fallback-card label { flex-direction: row-reverse; justify-content: space-between; width: 100%; }
.st-key-fallback-card label p { font-weight: 700; font-size: 17px; }
.sb-hint { font-size: 14px; color: #B9D3CE !important; }
.sb-kpi { padding: 20px; border-radius: 10px; background: var(--deep); }
.sb-label { font-size: 14px; letter-spacing: .08em; text-transform: uppercase; color: var(--mint) !important;
            font-weight: 700; }
.sb-kpi-row { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; margin-top: 4px; }
.sb-big { font-family: var(--serif); font-size: 64px; font-weight: 700; line-height: 1; }
.sb-proj { background: var(--mint); color: var(--dark) !important; font-weight: 700; font-size: 18px; padding: 3px 10px;
           border-radius: 6px; display: inline-block; }
.sb-proj-note { font-size: 13px; color: #B9D3CE !important; display: block; }
.sb-stat { display: flex; justify-content: space-between; align-items: baseline; padding: 12px 2px;
           border-bottom: 1px solid rgba(143,211,196,.2); }
.sb-stat:last-child { border-bottom: 0; }
.sb-stat span:first-child { color: #D6ECE7 !important; }
.sb-stat span:last-child { font-family: var(--serif); font-size: 30px; font-weight: 700; }
.st-key-reset button { background: transparent; border: 1.5px solid var(--mint); border-radius: 10px; padding: 12px;
                       font-size: 16px; font-weight: 700; }
.st-key-reset button * { color: var(--mint) !important; }
.st-key-reset button:hover { background: rgba(143,211,196,.12); border-color: var(--mint); }
.sb-section { border-top: 1px solid rgba(143,211,196,.2); padding-top: 14px; display: flex; flex-direction: column; gap: 6px; }
.sb-group { font-size: 13px; font-weight: 700; color: #D6ECE7 !important; margin-top: 6px; }
.sb-item { font-size: 15px; display: flex; gap: 8px; align-items: baseline; }
.sb-dot { width: 6px; height: 6px; border-radius: 50%; flex: none; transform: translateY(-2px); }
.sb-note { font-size: 14px; color: #B9D3CE !important; }

/* ---------- portfolio ---------- */
.fallback-banner { background: var(--amber-l); border: 1px solid var(--amber); border-radius: 8px; padding: 10px 16px;
                   font-size: 16px; margin-bottom: 8px; }
.page-date { color: var(--slate); font-size: 16px; }
.page-title { margin: 2px 0 0; font-family: var(--serif); font-size: 38px; font-weight: 700; line-height: 1.1; }
.page-sub { color: var(--slate); font-size: 16px; margin-top: 4px; }
.prog-text { font-size: 16px; font-weight: 700; display: flex; gap: 8px; align-items: center; }
.prog-bar { height: 10px; border-radius: 5px; background: var(--card); overflow: hidden; margin-top: 8px; }
.prog-bar > div { height: 100%; background: var(--teal); transition: width .4s; }
.st-key-analyze button { border: 1.5px solid var(--teal); background: #FFFFFF; color: var(--teal); font-weight: 700;
                         font-size: 15px; border-radius: 8px; padding: 4px 12px; min-height: 0; }
.st-key-analyze button:hover { background: #F4FAF8; border-color: var(--teal); color: var(--teal); }
.cp-table, .st-key-cp-table { border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }
.st-key-cp-table { gap: 0 !important; }
.cp-grid { display: grid; align-items: center; column-gap: 12px; min-width: 900px;
           grid-template-columns: 64px minmax(170px, 1.25fr) minmax(150px, 1.1fr) minmax(250px, 1.9fr) 180px 120px; }
.cp-head-row { background: #F4FAF8; color: var(--slate); font-size: 13px; text-transform: uppercase; letter-spacing: .05em;
               font-weight: 700; padding: 12px 0; }
.cp-head-row > div:first-child, .cp-row > div:first-child { padding-left: 14px; }
.cp-row { border-top: 1px solid var(--line); background: #FFFFFF; padding: 12px 0; font-size: 16px; }
.cp-pos { width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
          font-weight: 700; font-size: 15px; }
.cp-name { font-weight: 700; font-size: 18px; white-space: nowrap; }
.cp-biz { color: var(--slate); font-size: 14px; white-space: nowrap; }
.cp-chips { display: flex; flex-wrap: wrap; gap: 5px; }
.cp-chip { font-size: 14px; padding: 2px 8px; border-radius: 6px; background: var(--neutral); color: var(--slate);
           white-space: nowrap; }
.cp-offer { display: flex; flex-direction: column; gap: 6px; padding-right: 8px; }
.cp-offer-line { display: flex; align-items: center; justify-content: space-between; gap: 10px; line-height: 1.3; }
.cp-offer-line b { font-size: 15px; }
.cp-tag { font-size: 11px; font-weight: 700; letter-spacing: .05em; padding: 2px 7px; border-radius: 5px; color: #FFF;
          white-space: nowrap; }
.cp-pill { display: inline-flex; align-items: center; gap: 10px; padding: 4px 14px 4px 6px; border-radius: 22px; }
.cp-dot { width: 26px; height: 26px; border-radius: 50%; flex: none; }
.cp-score { font-family: var(--serif); font-size: 28px; font-weight: 700; color: var(--dark); line-height: 1.1; }
.cp-badge { font-size: 13px; font-weight: 700; padding: 4px 9px; border-radius: 6px; white-space: nowrap; }
.cp-work { display: flex; flex-direction: column; gap: 3px; font-size: 14px; font-weight: 700; }
.spin { display: inline-block; width: 12px; height: 12px; border: 2px solid currentColor; border-right-color: transparent;
        border-radius: 50%; animation: cp-spin .8s linear infinite; vertical-align: -1px; }
@keyframes cp-spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .spin { animation: none; } }
/* Whole row is clickable: an invisible button is stretched over it. */
[class*="st-key-rowwrap-"] { position: relative; gap: 0 !important; }
[class*="st-key-rowwrap-"]:hover .cp-row { background: #F4FAF8; }
[class*="st-key-rowwrap-"]:has(button:focus-visible) .cp-row { outline: 2px solid var(--mint); outline-offset: -2px; }
[class*="st-key-open-"], [class*="st-key-retry-"] { position: absolute; inset: 0; z-index: 2; }
[class*="st-key-open-"] > div, [class*="st-key-retry-"] > div, [class*="st-key-open-"] button,
[class*="st-key-retry-"] button { width: 100%; height: 100%; }
[class*="st-key-open-"] button, [class*="st-key-retry-"] button { opacity: 0; cursor: pointer; }
.retry-chip { font-size: 13px; font-weight: 700; padding: 3px 10px; border-radius: 6px; border: 1.5px solid var(--risk);
              color: var(--risk); display: inline-block; margin-top: 4px; }
.table-note { font-size: 15px; color: var(--slate); margin-top: 8px; }

/* ---------- detail ---------- */
.st-key-detail-head { position: relative; margin-bottom: 10px; }
.dt-head { background: var(--dark); color: #FFF; border-radius: 10px; padding: 18px 88px 18px 28px; display: flex;
           flex-wrap: wrap; gap: 14px 24px; align-items: center; justify-content: space-between; }
.dt-who { display: flex; gap: 16px; align-items: center; }
.dt-icon { width: 48px; height: 48px; border-radius: 50%; background: var(--teal); display: flex; align-items: center;
           justify-content: center; font-size: 22px; flex: none; }
.dt-name { font-family: var(--serif); font-size: 28px; font-weight: 700; line-height: 1.1; }
.dt-sub { color: var(--mint); font-size: 15px; }
.dt-prio { background: var(--mint); color: var(--dark); border-radius: 8px; padding: 4px 10px; font-size: 14px;
           white-space: nowrap; }
.dt-prio b { font-family: var(--serif); font-size: 24px; }
.st-key-close-detail { position: absolute; right: 22px; top: 50%; transform: translateY(-50%); width: auto !important; }
.st-key-close-detail button { width: 44px; height: 44px; border: 1.5px solid var(--mint); border-radius: 10px;
                              background: transparent; color: var(--mint); }
.st-key-close-detail button:hover { background: rgba(143,211,196,.12); color: var(--mint); border-color: var(--mint); }

[class*="st-key-offer-card-"] { border: 2px solid var(--amber); border-radius: 10px; overflow: hidden; gap: 12px !important;
                               padding: 0 18px 18px; }
.orq-band { background: var(--deep); color: #FFF; padding: 14px 18px; margin: 0 -18px; display: flex; gap: 12px;
            align-items: flex-start; }
.orq-label { font-size: 13px; font-weight: 700; letter-spacing: .1em; color: var(--mint); }
.orq-text { font-size: 17px; }
[class*="st-key-ai-"], [class*="st-key-manual-"] { border-radius: 10px; padding: 12px 14px; }
[class*="st-key-ai-"] { background: var(--card); border: 1px solid var(--line2); }
[class*="st-key-manual-"] { background: #FFFFFF; border: 1px solid var(--line); }
.ai-flag { font-size: 12px; font-weight: 700; letter-spacing: .06em; color: var(--deep); }
.item-name { font-weight: 700; font-size: 18px; }
.item-tag { font-size: 13px; font-weight: 700; }
[class*="st-key-amtwrap-"] [data-testid="stNumberInputContainer"] { border: 2px solid var(--line2); border-radius: 8px; }
[class*="st-key-amtwrap-over-"] [data-testid="stNumberInputContainer"] { border-color: var(--risk); }
[class*="st-key-amtwrap-"] input { font-family: var(--serif); font-size: 22px; font-weight: 700; text-align: right; }
[class*="st-key-amtwrap-over-"] input { color: var(--risk); }
.amt-hint { font-size: 13px; font-weight: 700; text-align: right; white-space: nowrap; }
[class*="st-key-rm-"] button { width: 40px; height: 40px; min-height: 0; padding: 0; border: 1.5px solid #B5C7CE;
                               border-radius: 8px; color: var(--slate); }
[class*="st-key-rm-"] button:hover { border-color: var(--risk); color: var(--risk); }
[class*="st-key-open-add-"] button { width: 100%; border: 1.5px dashed var(--teal); color: var(--teal); font-weight: 700;
                                     font-size: 16px; border-radius: 10px; }
[class*="st-key-open-add-"] button:hover { background: #F4FAF8; color: var(--teal); border-color: var(--teal); }
.err-box { background: var(--risk-l); border: 1.5px solid var(--risk); border-radius: 10px; padding: 12px 16px; }
.err-box b { display: block; }
.field-label { font-size: 13px; font-weight: 700; color: var(--slate); text-transform: uppercase; letter-spacing: .06em; }
.field-help { font-size: 13px; color: var(--slate); margin-bottom: 6px; }
[class*="st-key-approve-"] button { background: var(--teal); color: #FFF; border: 0; font-size: 18px; font-weight: 700;
                                    padding: 10px 22px; border-radius: 10px; }
[class*="st-key-approve-"] button:hover { background: var(--deep); color: #FFF; }
[class*="st-key-reject-"] button { border: 1.5px solid var(--slate); color: var(--slate); font-size: 18px; font-weight: 700;
                                   padding: 10px 22px; border-radius: 10px; }
.you-decide { font-size: 14px; color: var(--slate); padding-top: 14px; }
.ok-title { font-weight: 700; color: var(--teal); font-size: 17px; }
.ok-item { background: var(--card); border-radius: 8px; padding: 8px 12px; font-weight: 700; font-size: 17px; margin-top: 8px; }

[class*="st-key-chat-card-"] { border: 1px solid var(--line); border-radius: 10px; padding: 0 16px 14px; }
[class*="st-key-chat-card-"] [data-testid="stTab"] { flex: 1; justify-content: center; padding: 12px; }
[class*="st-key-chat-card-"] [data-testid="stTab"] p { font-weight: 700; font-size: 16px; }
[class*="st-key-chat-card-"] [data-testid="stTab"][data-key="0"] * { color: var(--teal); }
[class*="st-key-chat-card-"] [data-testid="stTab"][data-key="1"] * { color: var(--risk); }
.bubbles { display: flex; flex-direction: column; gap: 10px; }
.bubble { max-width: 88%; border-radius: 10px; padding: 10px 14px; font-size: 16px; display: flex; flex-direction: column; gap: 4px; }
.bubble.user { align-self: flex-end; background: var(--amber-l); }
[class*="st-key-chip-"] button { border-radius: 14px; border: 1px solid var(--line2); color: var(--deep); font-size: 14px;
                                 padding: 4px 11px; min-height: 0; width: 100%; height: 100%; }
[class*="st-key-chip-"] button p { white-space: normal; line-height: 1.25; }
[class*="st-key-chip-"] button:hover { background: var(--card); color: var(--deep); border-color: var(--line2); }

.brief { border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }
.brief-head { background: var(--card); padding: 14px 20px; display: flex; flex-wrap: wrap; gap: 6px 16px; align-items: baseline; }
.brief-head .serif { font-size: 22px; }
.brief-body { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 24px; padding: 20px; }
.brief-col { display: flex; flex-direction: column; gap: 10px; }
.brief-col > b { font-size: 17px; }
.tp { display: flex; gap: 10px; align-items: flex-start; }
.tp-n { width: 24px; height: 24px; border-radius: 50%; background: var(--teal); color: #FFF; flex: none; display: flex;
        align-items: center; justify-content: center; font-weight: 700; font-size: 13px; }
.obj { background: #F4FAF8; border-radius: 8px; padding: 10px 14px; }
.brief-next { background: var(--amber-l); border-top: 1px solid var(--amber); padding: 12px 20px; font-size: 17px; }

.pf-title { border-top: 1px solid var(--line); padding-top: 22px; margin-top: 8px; font-family: var(--serif);
            font-size: 26px; font-weight: 700; }
.pf-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; }
.pf-stat { background: var(--card); border-radius: 10px; padding: 16px; }
.pf-k { font-size: 13px; font-weight: 700; color: var(--slate); text-transform: uppercase; letter-spacing: .06em; }
.pf-v { font-family: var(--serif); font-size: 32px; font-weight: 700; line-height: 1.1; margin-top: 4px; }
.pf-s { color: var(--slate); font-size: 15px; }
.pf-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 20px; margin-top: 20px; }
.pf-card { border: 1px solid var(--line); border-radius: 10px; padding: 18px 20px; }
.pf-card-t { font-family: var(--serif); font-size: 21px; font-weight: 700; }
.pf-legend { display: flex; gap: 12px; font-size: 14px; color: var(--slate); }
.pf-legend i { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 5px; }
.bars { height: 150px; display: flex; align-items: flex-end; gap: 3px; border-bottom: 1px solid var(--line); }
.bars > div { flex: 1; height: 100%; display: flex; flex-direction: column; justify-content: flex-end; }
.axis { display: flex; justify-content: space-between; font-size: 13px; color: var(--slate); margin-top: 4px; }
.empty-chart { height: 150px; display: flex; align-items: center; justify-content: center; color: var(--slate);
               font-size: 16px; background: #F4FAF8; border-radius: 8px; margin-top: 10px; }
.meter { height: 10px; border-radius: 5px; background: var(--card); overflow: hidden; }
.mora { display: grid; grid-template-columns: repeat(12, 1fr); gap: 3px; }
.mora > div { display: flex; flex-direction: column; gap: 2px; align-items: center; }
.mora-cell { width: 100%; height: 30px; border-radius: 4px; display: flex; align-items: center; justify-content: center;
             font-size: 12px; font-weight: 700; }
.prod-row { display: flex; justify-content: space-between; align-items: center; gap: 10px; padding: 10px 0;
            border-top: 1px solid var(--card); }
.elig { font-size: 13px; font-weight: 700; padding: 2px 8px; border-radius: 6px; border: 1.5px solid var(--teal); color: #006157; }
.tl { display: flex; gap: 14px; align-items: stretch; }
.tl-rail { display: flex; flex-direction: column; align-items: center; width: 14px; flex: none; }
.tl-rail i { width: 12px; height: 12px; border-radius: 50%; margin-top: 5px; }
.tl-rail span { flex: 1; width: 2px; background: var(--line); }
.recs { background: var(--deep); color: #FFF; border-radius: 10px; padding: 22px 24px; display: flex; flex-direction: column;
        gap: 16px; margin-top: 20px; }
.interest { font-size: 14px; padding: 3px 10px; border-radius: 14px; background: rgba(143,211,196,.18); color: var(--mint);
            font-weight: 700; }
.rec-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 12px; }
.rec { background: #FFF; color: var(--dark); border-radius: 10px; padding: 16px; display: flex; flex-direction: column; gap: 8px; }
.rec-badge { font-size: 12px; font-weight: 700; padding: 2px 8px; border-radius: 6px; }

/* ---------- add product dialog ---------- */
.dlg-sub { font-size: 15px; color: var(--slate); margin-top: -8px; }
[role="dialog"] h2 { font-family: var(--serif); font-size: 22px; }
.dlg-col { font-size: 13px; font-weight: 700; letter-spacing: .08em; padding-bottom: 6px; }
[class*="st-key-catrow-"] { border-top: 1px solid var(--card); padding: 8px 0; }
[class*="st-key-addb-"] button { border: 1.5px solid var(--teal); color: var(--teal); font-weight: 700; font-size: 14px;
                                 border-radius: 8px; padding: 4px 12px; min-height: 0; }
[class*="st-key-adda-"] button { border: 1.5px solid var(--amber); color: var(--dark); font-weight: 700; font-size: 14px;
                                 border-radius: 8px; padding: 4px 12px; min-height: 0; }
.in-offer { font-size: 13px; font-weight: 700; color: var(--teal); white-space: nowrap; }
.has-it { font-size: 13px; color: var(--slate); white-space: nowrap; }
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


def html_block(markup, target=None):
    (target or st).markdown(markup, unsafe_allow_html=True)


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


def approved_counts():
    decisions = st.session_state.decisions.values()
    approved = [d for d in decisions if d["status"] == "APROBADA"]
    return len(approved), sum(len(d["approved"]) for d in approved)


# ---------- sidebar ----------

def sidebar():
    ss = st.session_state
    state = ss.state
    offers, items = approved_counts()
    vetoes = sum(r["result"]["vetoes"] for r in ss.runs.values() if r["status"] == "done")
    state["stats"].update(approved_offers=offers, vetoes=vetoes)
    now, projected = products_per_client(state), projected_products_per_client(state, items)
    done = sum(r["status"] == "done" for r in ss.runs.values())
    with st.sidebar:
        html_block("<div class='sb-brand'><div class='sb-logo'>🧭</div><div><div class='sb-title'>Crosspilot</div>"
                   "<div class='sb-sub'>Priorización y pre-visita</div></div></div>")
        with st.container(key="fallback-card"):
            st.toggle("Modo respaldo", key="fallback")
            html_block("<div class='sb-hint'>Plan B sin API</div>")
        proj = (f"<div><span class='sb-proj'>→ {projected:.1f}</span><span class='sb-proj-note'>si aceptan lo aprobado"
                f"</span></div>") if projected > now else ""
        html_block(f"<div class='sb-kpi'><div class='sb-label'>Productos por cliente</div><div class='sb-kpi-row'>"
                   f"<div class='sb-big'>{now:.1f}</div>{proj}</div></div>")
        html_block("<div>" + "".join(f"<div class='sb-stat'><span>{label}</span><span>{value}</span></div>" for label, value in [
            ("Clientes analizados", f"{done}/{len(state['clients'])}"), ("Ofertas aprobadas", offers),
            ("Vetos de riesgo", vetoes)]) + "</div>")
        if st.button("Reiniciar demo", key="reset", icon=":material/restart_alt:", use_container_width=True):
            init_session(reset=True)
            st.rerun()
        bank = "".join(f"<div class='sb-item'><i class='sb-dot' style='background:#8FD3C4'></i>{esc(name(p))}</div>"
                       for p in rules.bank_products(state))
        allies = "".join(
            f"<div class='sb-item'><i class='sb-dot' style='background:#F2B134'></i><span>{esc(p['name'])} "
            f"<span style='color:#B9D3CE'>· {esc(p['brand'])}</span></span></div>"
            for p in state["catalog"].values() if p["type"] == "aliado")
        html_block(f"<div class='sb-section'><div class='sb-label'>Productos para ofrecer</div>"
                   f"<div class='sb-group'>Del banco</div>{bank}<div class='sb-group'>De aliados</div>{allies}"
                   f"<div class='sb-note' style='margin-top:6px'>Aliados de ejemplo, sin acuerdo comercial.</div></div>")
        html_block("<div class='sb-note sb-section'>Próximo módulo: registro post-visita (en evolución).</div>")


# ---------- portfolio table ----------

def offer_cell(run, stage):
    if run["status"] == "error":
        return (f"<span style='color:#C2410C;font-weight:700;font-size:14px'>⚠ {esc(run['error'])}</span><br>"
                f"<span class='retry-chip'>Reintentar</span>")
    if run["status"] != "done":
        if stage in (None, "queued"):
            return "<span class='muted' style='font-size:15px'>En cola</span>"
        vc = "✓" if stage == "risk" else "<i class='spin'></i>"
        risk = "<i class='spin'></i>" if stage == "risk" else "·"
        return (f"<div class='cp-work'><span style='color:#007F73'>{vc} Venta cruzada</span>"
                f"<span style='color:#C2410C'>{risk} Riesgo</span></div>")
    res = run["result"]
    if not res["decisions"]:
        return "<span class='muted' style='font-size:15px'>Sin oferta viable</span>"
    lines = []
    for d in res["decisions"]:
        amount = d["max_amount"] if d["decision"] == rules.CONTRAOFERTA else d.get("amount")
        label = name(d["product_id"], short=True) + (f" {rules.fmt_soles(amount)}" if amount is not None else "")
        lines.append(f"<div class='cp-offer-line'><b>{esc(label)}</b><span class='cp-tag' "
                     f"style='background:{TAG_COLORS[d['decision']]}'>{d['decision']}</span></div>")
    return "<div class='cp-offer'>" + "".join(lines) + "</div>"


def row_html(pos, row, stage):
    ss = st.session_state
    cid, run, score = row["cid"], row["run"], row["score"]
    client = ss.state["clients"][cid]
    top = score is not None and pos <= 3
    position = (f"<div class='cp-pos' style='background:{'#0B4F57' if top else '#EEF2F3'};"
                f"color:{'#FFF' if top else '#4A6572'}'>{pos}</div>")
    who = f"<div class='cp-name'>{esc(client['name'])}</div><div class='cp-biz'>{esc(client['business'])}</div>"
    chips = "<div class='cp-chips'>" + "".join(
        f"<span class='cp-chip'>{esc(name(p, short=True))}</span>" for p in client["products"]) + "</div>"
    if score is None:
        priority = "<span style='color:#B5C7CE'>—</span>"
    else:
        dot, bg = light(score)
        priority = (f"<div class='cp-pill' style='background:{bg}'><span class='cp-dot' style='background:{dot}'>"
                    f"</span><span class='cp-score'>{score}</span></div>")
    decision = ss.decisions.get(cid)
    status = ""
    if decision:
        label, bg, fg = STATUS_BADGES[decision["status"]]
        status = f"<span class='cp-badge' style='background:{bg};color:{fg}'>{label}</span>"
    cells = [position, who, chips, offer_cell(run, stage), priority, status]
    return "<div class='cp-grid cp-row'>" + "".join(f"<div>{c}</div>" for c in cells) + "</div>"


def head_html():
    return "<div class='cp-grid cp-head-row'>" + "".join(f"<div>{t}</div>" for t in HEADERS) + "</div>"


def progress_html(done, total, running):
    if done == total:
        text = f"<span style='color:#007F73'>✓</span> {total} clientes analizados en paralelo"
    elif running:
        text = f"<i class='spin' style='color:#007F73'></i> Agentes analizando en paralelo · {done}/{total}"
    else:
        text = f"{done}/{total} analizados"
    return (f"<div class='prog-text'>{text}</div>"
            f"<div class='prog-bar'><div style='width:{done / total * 100:.0f}%'></div></div>")


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
        html_block(progress_html(len(ss.runs), len(cids), running=True), progress_slot)
        rows = "".join(row_html(pos, row, stages[row["cid"]]) for pos, row in enumerate(scored_rows(), start=1))
        html_block(f"<div class='cp-table'>{head_html()}{rows}</div>", table_slot)

    paint()
    run_portfolio(ss.state, cids, fake=fake_mode(), on_stage=on_stage, on_done=on_done, on_tick=paint,
                  pace=1.0 if fake_mode() else 0)


def portfolio_page():
    ss = st.session_state
    n = len(ss.state["clients"])
    if fake_mode():
        html_block("<div class='fallback-banner'>🛟 <b>Modo respaldo activo.</b> Respuestas predefinidas, sin llamar a "
                   "la API.</div>")
    head, side = st.columns([2.2, 1], vertical_alignment="bottom", gap="large")
    html_block(f"<div class='page-date'>{today_label()} · {n} clientes agendados</div>"
               "<div class='page-title'>Cartera priorizada del día</div>"
               "<div class='page-sub'>Prioridad de visita: probabilidad de que el cliente adquiera más productos, "
               "con la oferta ya validada por Riesgo.</div>", head)
    with side:
        progress_slot = st.empty()
        clicked = st.button("Analizar cartera", key="analyze", icon=":material/play_arrow:")
    table_slot = st.empty()
    if clicked or not ss.auto_started:
        ss.auto_started = True
        analyze(progress_slot, table_slot)
        st.rerun()
    done = sum(r["status"] == "done" for r in ss.runs.values())
    html_block(progress_html(done, n, running=False), progress_slot)
    with table_slot.container(key="cp-table"):
        html_block(head_html())
        for pos, row in enumerate(scored_rows(), start=1):
            render_row(pos, row)
    html_block("<div class='table-note'>El puntaje es un apoyo, no una decisión: el ejecutivo valida en terreno y "
               "aprueba cada oferta. Haz clic en un cliente para ver su análisis.</div>")


def render_row(pos, row):
    ss = st.session_state
    cid, run = row["cid"], row["run"]
    with st.container(key=f"rowwrap-{cid}"):
        html_block(row_html(pos, row, None))
        if run["status"] == "error":
            if st.button(f"Reintentar {cid}", key=f"retry-{cid}"):
                with st.spinner(f"Reintentando {ss.state['clients'][cid]['name']}…"):
                    store_run(cid, run_one(ss.state, cid, fake=fake_mode()))
                st.rerun()
        elif run["status"] == "done" and st.button(f"Ver {ss.state['clients'][cid]['name']}", key=f"open-{cid}"):
            ss.detail = cid
            st.rerun()


# ---------- detail page ----------

@st.dialog("Agregar producto", width="large")
def add_product_dialog(cid):
    ss = st.session_state
    state, decision = ss.state, ss.decisions[cid]
    client = state["clients"][cid]
    credit_blocked = decision["limited"] or decision["status"] == "SIN_OFERTA"
    html_block(f"<div class='dlg-sub'>Para {esc(client['name'])}</div>")
    bank_col, ally_col = st.columns(2, gap="large")
    html_block("<div class='dlg-col' style='color:#007F73'>DEL BANCO</div>", bank_col)
    html_block("<div class='dlg-col' style='color:#9A6A00'>DE ALIADOS</div>", ally_col)

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
        blocked = credit and (credit_blocked or rules.decide(state, pid, check) == rules.VETO)
        note = ("Crédito" if credit and pid in client["products"] else "No elegible hoy" if blocked else
                f"Hasta {rules.fmt_soles(check['max_amount'])}" if credit else "Sin crédito")
        with bank_col.container(key=f"catrow-{cid}-{pid}"):
            left, right = st.columns([3, 1.2], vertical_alignment="center")
            html_block(f"<div class='item-name' style='font-size:17px'>{esc(name(pid))}</div>"
                       f"<div class='muted' style='font-size:14px'>{note}</div>", left)
            if pid in client["products"]:
                html_block("<span class='has-it'>Ya lo tiene</span>", right)
            elif pid in decision["list"]:
                html_block("<span class='in-offer'>✓ En la oferta</span>", right)
            elif not blocked and right.button("+ Agregar", key=f"addb-{cid}-{pid}"):
                add(pid)
    for pid, product in state["catalog"].items():
        if product["type"] != "aliado":
            continue
        rec = next((r for r in client["recommendations"] if r["brand"] == product["brand"]), None)
        affinity = f" <b style='color:#0B4F57'>· Afinidad {rec['prob']}%</b>" if rec else ""
        with ally_col.container(key=f"catrow-{cid}-{pid}"):
            left, right = st.columns([3, 1.2], vertical_alignment="center")
            html_block(f"<div class='item-name' style='font-size:17px'>{esc(product['name'])}</div>"
                       f"<div class='muted' style='font-size:14px'>{esc(product['brand'])}{affinity}</div>", left)
            if pid in decision["list"]:
                html_block("<span class='in-offer'>✓ En la oferta</span>", right)
            elif right.button("+ Agregar", key=f"adda-{cid}-{pid}"):
                add(pid)
    html_block("<div class='field-help' style='text-align:right'>Aliados de ejemplo, sin acuerdo comercial.</div>",
               ally_col)


def offer_items(cid, res, decision):
    ss = st.session_state
    state = ss.state
    ai = {i["product_id"]: i for i in res["items"]}
    for pid in list(decision["list"]):
        is_ai, credit = pid in ai, rules.is_credit(state, pid)
        product = state["catalog"][pid]
        if is_ai:
            item = ai[pid]
            counter = item["decision"] == rules.CONTRAOFERTA
            tag = (f"Contraoferta de Riesgo · propuesto {rules.fmt_soles(item['proposed_amount'])}" if counter
                   else "Aprobado por Riesgo")
            tag_color = "#C2410C" if counter else "#007F73"
        else:
            tag = ("Agregado por ti · Riesgo lo valida al aprobar" if credit else
                   f"Agregado por ti · Aliado {product['brand']}" if product["type"] == "aliado" else "Agregado por ti")
            tag_color = "#4A6572"
        with st.container(key=f"{'ai' if is_ai else 'manual'}-{cid}-{pid}"):
            left, mid, right = st.columns([3, 1.8, 0.45], vertical_alignment="center")
            flag = "<div class='ai-flag'>✨ RECOMENDADO POR IA</div>" if is_ai else ""
            html_block(f"{flag}<div class='item-name'>{esc(product['name'])}</div>"
                       f"<div class='item-tag' style='color:{tag_color}'>{esc(tag)}</div>", left)
            if credit:
                max_amount = rules.check_policy(state, cid, pid)["max_amount"] or 0
                key = f"amt-{cid}-{pid}"
                current = int(ss.get(key, decision["amounts"][pid] or 0))
                over = current > max_amount
                with mid.container(key=f"amtwrap-{'over' if over else 'ok'}-{cid}-{pid}"):
                    amount = st.number_input("Monto en soles", min_value=0, step=500, value=current, key=key,
                                             label_visibility="collapsed")
                decision["amounts"][pid] = int(amount)
                html_block(f"<div class='amt-hint' style='color:{'#C2410C' if over else '#4A6572'}'>"
                           f"{'Supera el máximo' if over else 'Máximo permitido'}: {rules.fmt_soles(max_amount)}</div>",
                           mid)
            if right.button("", key=f"rm-{cid}-{pid}", icon=":material/delete:", help="Quitar producto"):
                decision["list"].remove(pid)
                decision["errors"] = []
                st.rerun()


def approve(cid, decision, res):
    state = st.session_state.state
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
    status = decision["status"]
    with st.container(key=f"offer-card-{cid}"):
        html_block(f"<div class='orq-band'><span style='color:#8FD3C4;font-size:18px'>🧭</span><div>"
                   f"<div class='orq-label'>ORQUESTADOR</div><div class='orq-text'>{esc(res['closing'])}</div></div></div>")
        if status in ("PENDIENTE", "SIN_OFERTA"):
            if status == "SIN_OFERTA":
                html_block("<div class='muted' style='font-size:17px;padding-top:4px'><b style='color:#0F2A2E'>Sin oferta "
                           "viable.</b> Ningún crédito pasa la política hoy. Puedes agregar productos que no implican "
                           "crédito para el banco.</div>")
            offer_items(cid, res, decision)
            if st.button("+ Agregar producto", key=f"open-add-{cid}"):
                add_product_dialog(cid)
            if decision["errors"]:
                html_block("<div class='err-box'>⚠ <b>No se puede aprobar</b>"
                           + "".join(f"<div style='font-size:15px'>{esc(e)}</div>" for e in decision["errors"]) + "</div>")
            if status == "PENDIENTE":
                html_block("<div class='field-label'>Comentarios</div>")
                decision["comment"] = st.text_area(
                    "Comentarios", value=decision["comment"], key=f"comment-{cid}", height=68,
                    label_visibility="collapsed", placeholder="Por qué aceptas, ajustas o rechazas esta oferta")
                html_block("<div class='field-help'>Se guarda con la decisión para análisis posteriores.</div>")
                a, r, note = st.columns([1.25, 1, 1.2], vertical_alignment="center")
                if a.button("Aprobar oferta", key=f"approve-{cid}", icon=":material/check:", use_container_width=True):
                    approve(cid, decision, res)
                    st.rerun()
                if r.button("Rechazar", key=f"reject-{cid}", icon=":material/close:", use_container_width=True):
                    decision.update(status="RECHAZADA", errors=[])
                    st.rerun()
                html_block("<div class='you-decide' style='padding-top:0'>👔 Tú decides</div>", note)
            return
        if status == "APROBADA":
            html_block("<div class='ok-title' style='padding-top:4px'>✓ Oferta aprobada</div>" + "".join(
                f"<div class='ok-item'>{esc(name(i['product_id']))}"
                f"{' · ' + rules.fmt_soles(i['amount']) if i['amount'] is not None else ''}</div>"
                for i in decision["approved"]))
        else:
            html_block("<div class='muted' style='font-size:17px;padding-top:4px'>✕ Rechazaste la oferta. No se genera "
                       "ficha.</div>")
        if decision["comment"]:
            html_block(f"<div class='muted' style='font-size:15px'>💬 <b style='color:#0F2A2E'>Comentario:</b> "
                       f"{esc(decision['comment'])}</div>")


def brief_section(cid):
    ss = st.session_state
    decision, res = ss.decisions[cid], ss.runs[cid]["result"]
    if decision["status"] != "APROBADA":
        return
    if decision["brief_error"]:
        st.error(decision["brief_error"])
        if st.button("Reintentar ficha", key=f"brief-retry-{cid}"):
            make_brief(cid, decision, res)
            st.rerun()
        return
    brief = decision["brief"]
    if not brief:
        return
    points = "".join(f"<div class='tp'><div class='tp-n'>{n}</div><div>{esc(t)}</div></div>"
                     for n, t in enumerate(brief["talking_points"], start=1))
    objections = "".join(f"<div class='obj'><b>“{esc(o['objecion'])}”</b><div style='font-size:15px;margin-top:2px'>"
                         f"{esc(o['respuesta'])}</div></div>" for o in brief["objeciones"])
    html_block(f"<div class='brief'><div class='brief-head'><span class='serif'>Ficha de visita</span>"
               f"<span class='muted'>{esc(brief['resumen'])}</span></div><div class='brief-body'>"
               f"<div class='brief-col'><b>Puntos de conversación</b>{points}</div>"
               f"<div class='brief-col'><b>Objeciones probables</b>{objections}</div></div>"
               f"<div class='brief-next'><span style='color:#9A6A00'>→</span> <b>Siguiente paso:</b> "
               f"{esc(brief['siguiente_paso'])}</div></div>")


def chat_section(cid):
    ss = st.session_state
    res = ss.runs[cid]["result"]
    with st.container(key=f"chat-card-{cid}"):
        tabs = st.tabs([f"{icon} {label}" for icon, label, _ in TABS.values()])
        for tab_key, tab in zip(TABS, tabs):
            label, agent_bg = TABS[tab_key][1], TABS[tab_key][2]
            with tab:
                history = ss.chats[cid][tab_key]
                with st.container(height=330, border=False):
                    bubbles = "".join(
                        f"<div class='bubble {'user' if m['role'] == 'user' else ''}' "
                        f"style='{'' if m['role'] == 'user' else f'background:{agent_bg}'}'>"
                        + "".join(f"<div>{esc(line)}</div>" for line in m["text"].split("\n")) + "</div>"
                        for m in history)
                    html_block(f"<div class='bubbles'>{bubbles}</div>")
                chips = st.columns(3)
                question = None
                for chip, text in zip(chips, CHIPS[tab_key]):
                    if chip.button(text, key=f"chip-{cid}-{tab_key}-{text}"):
                        question = text
                typed = st.chat_input(f"Pregunta o corrige a {label}", key=f"input-{cid}-{tab_key}")
                question = question or typed
                if question:
                    past = [{"role": m["role"], "text": m["text"]} for m in history]
                    history.append({"role": "user", "text": question})
                    with st.spinner(f"{label} está respondiendo…"):
                        try:
                            reply = agents.chat_reply(ss.state, cid, tab_key, question, past, res, fake=fake_mode())
                        except AgentError as exc:
                            reply = f"{exc}. Activa el Modo respaldo y vuelve a intentar."
                    history.append({"role": "agent", "text": reply})
                    st.rerun()


def profile_html(cid):
    state = st.session_state.state
    client = state["clients"][cid]
    year, policy = state["meta"]["reference_year"], state["policy"]
    late = client["max_days_late_12m"]
    sbs, sbs_bg, sbs_fg = (("Normal", "#007F73", "#FFF") if late <= 8 else ("CPP", "#F2B134", "#0F2A2E") if late <= 30
                           else ("Deficiente", "#C2410C", "#FFF"))
    hist = client_history(state, cid)
    on_time = round(sum(v == 0 for v in hist["late_days"]) / 12 * 100)
    share = round(client["principality"] * 100)
    segment = rules.segment(client["monthly_net_income"])[0]
    stats = f"""<div class='pf-stats'>
<div class='pf-stat'><div class='pf-k'>Cliente del banco</div><div class='pf-v'>{year - client['bank_since']} años</div>
<div class='pf-s'>Desde {client['bank_since']} · {segment}</div></div>
<div class='pf-stat'><div class='pf-k'>En el sistema financiero</div><div class='pf-v'>{year - client['system_since']} años</div>
<div class='pf-s'>Desde {client['system_since']}</div></div>
<div class='pf-stat'><div class='pf-k'>Principalidad</div><div class='pf-v' style='color:#007F73'>{share}%</div>
<div class='meter' style='background:#FFF;height:8px;margin-top:8px'><div style='height:100%;width:{share}%;background:#007F73'></div></div>
<div class='pf-s' style='font-size:14px;margin-top:6px'>De su deuda y ahorro está en el banco</div></div>
<div class='pf-stat'><div class='pf-k'>Mora · 12 meses</div><div style='display:flex;gap:10px;align-items:center;margin-top:4px'>
<span class='pf-v' style='margin:0'>{late} días</span><span class='cp-badge' style='background:{sbs_bg};color:{sbs_fg}'>{sbs}</span></div>
<div class='pf-s'>Atraso máximo · {on_time}% de meses al día</div></div></div>"""

    axis = "".join(f"<span>{hist['months'][t]}</span>" for t in (0, 6, 12, 18, 23))
    legend = ("<div class='pf-legend'><span><i style='background:#007F73'></i>Banco</span>"
              "<span><i style='background:#B5C7CE'></i>Otras entidades</span></div>")
    capacity = policy["debt_multiple"] * client["monthly_net_income"]
    debt = client["current_debt"]
    if debt:
        top = max(1, max(b + o for b, o in zip(hist["debt_bank"], hist["debt_other"])))
        bars = "".join(f"<div><div style='height:{o / top * 100:.1f}%;background:#B5C7CE;border-radius:2px 2px 0 0'></div>"
                       f"<div style='height:{b / top * 100:.1f}%;background:#007F73'></div></div>"
                       for b, o in zip(hist["debt_bank"], hist["debt_other"]))
        debt_chart = (f"<div class='muted' style='font-size:13px;margin:10px 0 4px'>Máx. "
                      f"{rules.fmt_soles(round(top / 500) * 500)}</div><div class='bars'>{bars}</div><div class='axis'>{axis}</div>")
    else:
        debt_chart = "<div class='empty-chart'>Sin deuda en el sistema financiero</div>"
    debt_card = f"""<div class='pf-card'><div style='display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px'>
<div class='pf-card-t'>Histórico de crédito · 24 meses</div>{legend}</div>{debt_chart}
<div style='margin-top:16px;display:flex;flex-direction:column;gap:6px'>
<div style='display:flex;justify-content:space-between;font-size:15px;flex-wrap:wrap;gap:4px'><span>Deuda total <b>{rules.fmt_soles(debt)}</b>
· en el banco {rules.fmt_soles(round(debt * client['principality']))}</span><span class='muted'>Capacidad {rules.fmt_soles(capacity)}</span></div>
<div class='meter'><div style='height:100%;width:{min(100, round(debt / capacity * 100))}%;background:#0B4F57'></div></div>
<div class='muted' style='font-size:14px'>Disponible según política ({policy['debt_multiple']} × ingreso):
<b style='color:#007F73'>{rules.fmt_soles(max(0, capacity - debt))}</b></div></div></div>"""

    savings = hist["savings"]
    if savings:
        top = max(savings)
        pts = " L".join(f"{t * 480 / 23:.1f},{116 - v / top * 100:.1f}" for t, v in enumerate(savings))
        sav_chart = (f"<div class='muted' style='font-size:13px;margin:10px 0 4px'>Máx. {rules.fmt_soles(round(top / 100) * 100)}</div>"
                     f"<svg viewBox='0 0 480 120' preserveAspectRatio='none' style='width:100%;height:150px;display:block;"
                     f"border-bottom:1px solid #D7E7E3'><path d='M0,120 L{pts} L480,120 Z' fill='#EAF4F2'></path>"
                     f"<path d='M{pts}' fill='none' stroke='#007F73' stroke-width='2.5' vector-effect='non-scaling-stroke'>"
                     f"</path></svg><div class='axis'>{axis}</div>")
        now = (f"<div style='font-size:15px'>Saldo hoy <b class='serif' style='font-size:19px;color:#007F73'>"
               f"{rules.fmt_soles(round(savings[-1] / 100) * 100)}</b></div>")
    else:
        sav_chart, now = "<div class='empty-chart'>Sin cuenta de ahorro en el banco</div>", ""

    def mora_colors(v):
        if v == 0:
            return "#EAF4F2", "#006157"
        if v <= 8:
            return "#FDF1D6", "#0F2A2E"
        return ("#F2B134", "#0F2A2E") if v <= 15 else ("#C2410C", "#FFFFFF")

    mora = "".join(f"<div><div class='mora-cell' style='background:{mora_colors(v)[0]};color:{mora_colors(v)[1]}'>"
                   f"{f'{v}d' if v else '0'}</div><span style='font-size:11px;color:#4A6572'>{m[:3]}</span></div>"
                   for v, m in zip(hist["late_days"], hist["late_months"]))
    sav_card = f"""<div class='pf-card'><div style='display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px'>
<div class='pf-card-t'>Histórico de ahorro · 24 meses</div>{now}</div>{sav_chart}
<div style='margin-top:16px'><div style='font-size:15px;margin-bottom:6px'>Días de atraso por mes · últimos 12</div>
<div class='mora'>{mora}</div></div></div>"""

    eligible = rules.eligible_products(state, cid)
    products = ""
    for pid in rules.bank_products(state):
        has = pid in client["products"]
        icon = ("<span style='color:#007F73;font-size:18px'>●</span>" if has
                else "<span style='color:#B5C7CE;font-size:18px'>○</span>")
        right = (f"<span class='muted' style='font-size:15px'>Desde {client['product_since'].get(pid, '').replace('-', '/')}</span>"
                 if has else "<span class='elig'>Elegible</span>" if pid in eligible
                 else "<span class='muted' style='font-size:14px'>No elegible hoy</span>")
        products += (f"<div class='prod-row'><div style='display:flex;gap:10px;align-items:center'>{icon}"
                     f"<span style='font-size:17px;font-weight:700'>{esc(name(pid))}</span></div>{right}</div>")
    events = [(str(client["system_since"]), "Primer producto en el sistema financiero", False)]
    if client["bank_since"] != client["system_since"]:
        events.append((str(client["bank_since"]), "Ingresa al banco", True))
    else:
        events[0] = (str(client["system_since"]), "Ingresa al sistema financiero con el banco", True)
    events += [(since.replace("-", "/"), f"Contrata {name(pid).lower()}", True)
               for pid, since in sorted(client["product_since"].items(), key=lambda kv: kv[1])]
    timeline = "".join(f"<div class='tl'><div class='tl-rail'><i style='background:{'#007F73' if bank else '#4A6572'}'>"
                       f"</i><span></span></div><div style='padding-bottom:14px'><div style='font-size:14px;font-weight:700;"
                       f"color:#4A6572'>{d}</div><div style='font-size:17px'>{esc(t)}</div></div></div>"
                       for d, t, bank in events)
    lists = f"""<div class='pf-grid'><div class='pf-card'><div class='pf-card-t' style='margin-bottom:8px'>Productos del banco</div>
{products}</div><div class='pf-card'><div class='pf-card-t' style='margin-bottom:12px'>Comportamiento desde su ingreso</div>
{timeline}</div></div>"""

    interests = "".join(f"<span class='interest'>{esc(i)}</span>" for i in client["interests"])
    recs = ""
    for r in sorted(client["recommendations"], key=lambda r: -r["prob"]):
        bank = r["brand"] == BANK_BRAND
        badge = ("<span class='rec-badge' style='background:#007F73;color:#FFF'>BANCO</span>" if bank
                 else "<span class='rec-badge' style='background:#F2B134;color:#0F2A2E'>ECOSISTEMA</span>")
        bar = "#007F73" if r["prob"] >= 75 else "#F2B134" if r["prob"] >= 60 else "#B5C7CE"
        recs += (f"<div class='rec'><div style='display:flex;justify-content:space-between;align-items:center;gap:8px'>"
                 f"<span style='font-size:14px;font-weight:700;color:#0B4F57'>{esc(r['brand'])}</span>{badge}</div>"
                 f"<div style='font-size:18px;font-weight:700;line-height:1.25'>{esc(r['product'])}</div>"
                 f"<div style='display:flex;align-items:center;gap:10px'><div class='meter' style='flex:1;height:8px'>"
                 f"<div style='height:100%;width:{r['prob']}%;background:{bar}'></div></div>"
                 f"<span class='serif' style='font-size:22px'>{r['prob']}%</span></div>"
                 f"<div class='muted' style='font-size:15px'>{esc(r['why'])}</div></div>")
    rec_card = f"""<div class='recs'><div style='display:flex;flex-wrap:wrap;gap:10px 20px;align-items:baseline;justify-content:space-between'>
<div class='serif' style='font-size:24px'>Intereses y productos con alta probabilidad</div>
<div style='display:flex;flex-wrap:wrap;gap:6px'>{interests}</div></div><div class='rec-grid'>{recs}</div>
<div style='font-size:14px;color:#B9D3CE'>Probabilidad estimada con datos sintéticos. Las marcas del ecosistema son un
ejemplo ilustrativo de alianzas, sin acuerdo comercial.</div></div>"""

    return (f"<div class='pf-title'>Perfil del cliente</div>{stats}<div class='pf-grid'>{debt_card}{sav_card}</div>"
            f"{lists}{rec_card}")


def detail_page(cid):
    ss = st.session_state
    client = ss.state["clients"][cid]
    rows = scored_rows()
    pos = next(i for i, r in enumerate(rows, start=1) if r["cid"] == cid)
    score = rows[pos - 1]["score"]
    with st.container(key="detail-head"):
        html_block(f"<div class='dt-head'><div class='dt-who'><div class='dt-icon'>🏪</div><div>"
                   f"<div class='dt-name'>{esc(client['name'])}</div><div class='dt-sub'>{cid} · {esc(client['business'])} · "
                   f"{esc(client['district'])} · Ingreso neto {rules.fmt_soles(client['monthly_net_income'])}/mes</div>"
                   f"</div></div><span class='dt-prio'>Prioridad <b>{score}</b> · #{pos}</span></div>")
        if st.button("", key="close-detail", icon=":material/close:", help="Volver a la cartera"):
            ss.detail = None
            st.rerun()
    left, right = st.columns(2, gap="medium")
    with left:
        offer_section(cid)
    with right:
        chat_section(cid)
    brief_section(cid)
    html_block(profile_html(cid))


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
