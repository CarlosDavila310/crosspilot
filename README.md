# Crosspilot

Copiloto multiagente de priorización y preparación de visitas para el ejecutivo de negocios de un banco de microfinanzas (MYPE). Analiza en paralelo la cartera del día, propone venta cruzada validada por Riesgo, da un puntaje único de prioridad de visita y deja que el ejecutivo apruebe cada oferta.

Hackathon Hack AI Agents Impact (NTT DATA × Sundai LATAM, Perú Tech Week 2026). Solo datos sintéticos.

**El LLM redacta, el código decide:** montos, decisiones de riesgo y prioridad salen de `crosspilot/rules.py`.

## Correr en local

```bash
python -m venv .venv && .venv/Scripts/activate      # Windows; en macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
CROSSPILOT_FAKE_LLM=1 streamlit run app.py           # modo respaldo, sin API
ANTHROPIC_API_KEY=... streamlit run app.py           # con Claude real
pytest -q                                             # nunca llama a la API
```

Variables (entorno o `.streamlit/secrets.toml`, que no se sube al repo):

- `ANTHROPIC_API_KEY`: key de Anthropic o de un gateway compatible con la API de Anthropic.
- `ANTHROPIC_BASE_URL`: opcional, URL del gateway (sin `/v1`). Vacío = api.anthropic.com.
- `CROSSPILOT_MODEL`: por defecto `claude-sonnet-5-5`.
- `CROSSPILOT_FAKE_LLM=1`: arranca en Modo respaldo.

Sin API key, la app arranca con el Modo respaldo encendido.

## Despliegue

Streamlit Community Cloud → nueva app desde este repo, archivo `app.py`, y en Secrets las mismas variables:

```toml
ANTHROPIC_API_KEY = "..."
ANTHROPIC_BASE_URL = "https://tu-gateway"   # opcional
CROSSPILOT_MODEL = "..."                    # opcional
```

URL del demo: https://crosspilot.streamlit.app/

## Estructura

- `app.py`: interfaz Streamlit (cartera, detalle, chat, perfil).
- `crosspilot/rules.py`: `check_policy`, `validate_offer`, `rank_clients`, `priority_score`, `validate_approval`.
- `crosspilot/orchestrator.py`: `run_pipeline` y `run_portfolio` (10 clientes en paralelo).
- `crosspilot/agents.py`, `llm.py`, `fakes.py`: agentes, bucle de tool use y modo respaldo.
- `data/seed.json`: cartera, catálogo, aliados de ejemplo (sin acuerdo comercial) y política.
- `specs/`, `design/`: especificación y prototipo de referencia.
