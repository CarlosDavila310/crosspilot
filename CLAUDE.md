# Crosspilot

Copiloto multiagente de **priorización y preparación de visitas** (pre-visita) para el ejecutivo de negocios de un banco de microfinanzas (MYPE). Analiza en paralelo la cartera del día, propone venta cruzada validada por riesgo, da un único puntaje de prioridad de visita y deja que el ejecutivo gestione y apruebe cada oferta.

Hackathon (un día, demo en vivo). Entregable: URL pública + repo + demo + pitch.

## Fuente de verdad (en este orden)
1. `specs/requirements_v2.md`: cambios tras la mentoría. **Manda sobre el spec original.**
2. `specs/brief_y_spec_original.md`: requisitos R1–R10, diseño técnico (§5 datos, §6 reglas, §7 agentes, §8 orquestador), tareas.
3. `design/README.md` + `design/Crosspilot v2.dc.html`: diseño hi-fi de referencia (HTML, no es código de producción).

Si código y spec no coinciden, el spec manda. Si el spec no cubre algo, pregunta antes de inventar.

## Stack
Python 3.11+, `streamlit`, `anthropic`, `pytest`. Nada más sin preguntar. Paralelismo con `concurrent.futures.ThreadPoolExecutor` (stdlib).

## Comandos
```bash
pip install -r requirements.txt
streamlit run app.py
CROSSPILOT_FAKE_LLM=1 streamlit run app.py   # modo respaldo, sin API
pytest -q                                     # nunca llama a la API
```

## Reglas
- **El LLM redacta, el código decide.** Montos, decisiones de riesgo, puntaje de prioridad y orden son deterministas (`rules.py`). El texto del LLM nunca cambia una decisión de `check_policy`.
- Sin frameworks de agentes. Un solo bucle de tool use (`llm.py`).
- Estado por sesión en `st.session_state`. Sin globales mutables.
- Valida en el borde: montos y productos que agrega el ejecutivo se revalidan con `check_policy` al aprobar.
- Solo datos sintéticos. API key solo por entorno / Secrets.
- UI y prompts en español; código en inglés.
- Una tarea a la vez; `pytest -q` verde; commit `T<id>: <resumen>`.

## No hacer
Auth, base de datos, Docker, async, colas, multiidioma, audio, NANDA Town, módulo post-visita (fuera del core; ver requirements_v2 §6).
