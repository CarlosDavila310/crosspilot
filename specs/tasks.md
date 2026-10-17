# Crosspilot: tareas

Roles: **D** Datos y reglas · **A** Agentes y herramientas · **I** Interfaz y despliegue · **P** Pitch e impacto.

Cada tarea dice qué archivos toca. **Un dueño por archivo**: así cuatro personas usan Claude Code en
paralelo sin pisarse. Para editar un archivo ajeno, se pide al dueño.

| Archivo | Dueño |
|---|---|
| `data/seed.json`, `crosspilot/data.py`, `crosspilot/rules.py`, `tests/test_rules.py` | D |
| `crosspilot/llm.py`, `crosspilot/agents.py`, `crosspilot/fakes.py`, `crosspilot/orchestrator.py`, `tests/test_flow.py` | A |
| `app.py`, `requirements.txt`, `.gitignore`, `README.md` | I |
| Guion, pitch, ensayo | P |

## Cómo pedirle cada tarea a Claude Code

```
Lee CLAUDE.md y los tres archivos de specs/. Implementa la tarea <ID> de specs/tasks.md.
Toca solo los archivos que indica la tarea. Escribe los tests que pide, corre pytest -q,
marca la tarea con [x] y dime qué quedó pendiente.
```

En tareas con más lógica (T2.2, T2.3, T3.1), pídele primero un plan breve, revísalo y luego dale luz verde.

---

## Sprint 0 · Antes del evento

- [ ] **T0.1 [todos]** Confirmar con los organizadores si se permite traer código o datos preparados.
  Si no, este spec es lo único que se lleva.
- [ ] **T0.2 [I]** Cuentas listas: GitHub, Streamlit Community Cloud y una API key de Anthropic con crédito.
- [ ] **T0.3 [todos]** Claude Code instalado y autenticado en al menos dos laptops.
- [ ] **T0.4 [todos]** Leer `requirements.md` y `design.md`. Cada quien conoce sus tareas.
- [ ] **T0.5 [P]** Borrador del guion (ver "Guion del demo" abajo).

---

## Sprint 1 · BUILD (10:45 – 13:00)

**Meta del checkpoint (13:20):** C01 pasa de datos a ficha de visita, con la API real y en modo respaldo.

- [x] **T1.1 [I] Esqueleto del repo** · 15 min
  - Archivos: `requirements.txt`, `.gitignore`, `app.py`, `crosspilot/__init__.py`, carpetas `data/` y `tests/`.
  - `app.py` muestra el título "Crosspilot" y una barra lateral vacía.
  - Hecho cuando: `streamlit run app.py` abre y `pytest -q` corre sin errores. Primer push a GitHub.

- [x] **T1.2 [D] Seed y estado** · 30 min · R1, R8, NF2
  - Archivos: `data/seed.json`, `crosspilot/data.py`, `tests/test_rules.py`.
  - `seed.json` exacto según design §5 (política, catálogo, 10 clientes, señales de C01 literales).
  - `new_state()` y `products_per_client(state)`.
  - Test: `products_per_client(new_state()) == 2.2`; `new_state()` devuelve copias independientes.

- [x] **T1.3 [D] Reglas: check_policy y validate_offer** · 40 min · R2.4, R3
  - Archivos: `crosspilot/rules.py`, `tests/test_rules.py`.
  - Según design §6.1 y §6.3, incluida la función que deriva APROBADO, CONTRAOFERTA o VETO.
  - Tests: C01 activo fijo por 20,000 da CONTRAOFERTA de 12,000; C03 crédito da VETO; no crédito
    nuevo da APROBADO; producto ya contratado da VETO; los 4 casos de descarte de `validate_offer`.

- [x] **T1.4 [D] Reglas: rank_clients** · 20 min · R1
  - Archivos: `crosspilot/rules.py`, `tests/test_rules.py`.
  - Según design §6.2.
  - Test: top 5 = `["C01","C02","C05","C07","C04"]`, puntajes `[1070, 950, 870, 800, 720]`.

- [ ] **T1.5 [A] Bucle de agentes y modo respaldo** · 40 min · R9
  - Archivos: `crosspilot/llm.py`, `crosspilot/fakes.py`.
  - `run_agent()` y `AgentError` según design §7.1.
  - `fakes.respond()` con `cross_sell` y `brief` de C01 (design §11). El resto, en T2.6.
  - Prueba manual: una llamada real devuelve el `input` de la herramienta de envío.

- [ ] **T1.6 [A] Agentes Venta cruzada y Visita** · 30 min · R2.1–R2.3, R6
  - Archivo: `crosspilot/agents.py`.
  - `cross_sell(state, client_id, fake)` y `visit_brief(state, client_id, items, pitch, fake)` con
    prompts y esquemas de design §7.2 y §7.4. El `enum` de `product_id` se arma desde el catálogo.

- [ ] **T1.7 [I] Flujo mínimo en la UI** · 40 min · R1, R6
  - Archivo: `app.py`.
  - Sección 1 (agenda + selector + "Preparar visita") y sección 4 (ficha).
  - Flujo provisional: `cross_sell`, luego `validate_offer`, luego `visit_brief`, sin riesgo ni
    aprobación. Se reemplaza en T2.3.
  - Toggle "Modo respaldo" ya funcionando.

**Checkpoint 13:20:** C01 de datos a ficha, con API y en fake. Si no sale, todo el equipo apoya a A.

---

## Sprint 2 · MAKE IT AGENTIC (14:00 – 15:30)

**Meta:** negociación visible, contraoferta de riesgo y aprobación humana.

- [ ] **T2.1 [A] Agente Riesgo** · 25 min · R3.5
  - Archivo: `crosspilot/agents.py`, `crosspilot/fakes.py` (risk de C01).
  - `risk_review(state, client_id, items, fake)` con `check_policy` como herramienta real (design §7.3).

- [ ] **T2.2 [A] Orquestador** · 40 min · R2.4, R2.5, R3, R4
  - Archivos: `crosspilot/orchestrator.py`, `tests/test_flow.py`.
  - `run_pipeline()` exacto según design §8, con los mensajes de log tal cual.
  - Test: C01 en fake da `PENDIENTE_APROBACION`, activo fijo 12,000 + seguro, y el log empieza y
    termina con ORQUESTADOR.

- [ ] **T2.3 [I] Negociación y aprobación en la UI** · 45 min · R4, R5
  - Archivo: `app.py`.
  - Reemplazar el flujo provisional por `run_pipeline`. Sección 2 (chat de agentes) y sección 3
    (incluir/editar/aprobar/rechazar con revalidación, design §9). La ficha sale solo tras aprobar.
  - Prueba manual: subir el monto de C01 a 15,000 y aprobar muestra error y bloquea la aprobación.

- [ ] **T2.4 [I] Barra lateral** · 20 min · R8, R10
  - Archivo: `app.py`.
  - 4 métricas, delta de productos por cliente frente a 2.2, botón "Reiniciar demo".

- [ ] **T2.5 [D] Revisión de datos para el demo** · 20 min · R3.3
  - Archivo: `data/seed.json`.
  - Revisar que las señales de los 10 clientes sean coherentes. Correr C03 y confirmar VETO visible.

- [ ] **T2.6 [A] Respaldo genérico** · 20 min · R9
  - Archivo: `crosspilot/fakes.py`.
  - Respuestas genéricas para los demás clientes (design §11).

- [ ] **T2.7 [P] Ensayo 1** · 15 min
  - Correr el guion completo en modo respaldo con cronómetro. Anotar lo que confunde.

**Mentoría 15:30:** mostrar el flujo de C01 y preguntar qué le falta al pitch de negocio.

---

## Sprint 3 · MAKE IT REAL (15:50 – 17:00)

**Meta:** flujo cerrado, URL pública y demo ensayado.

- [ ] **T3.1 [A+D] Post-visita y CRM** · 35 min · R7, R8.2
  - Archivos: `crosspilot/agents.py`, `crosspilot/fakes.py`, `crosspilot/rules.py` (validate_crm_entry),
    `app.py` (sección 5, coordinar con I), `tests/test_flow.py`.
  - Test: flujo completo de C01 en fake (aprobar y registrar ACEPTO) lleva productos por cliente de 2.2 a 2.4.

- [ ] **T3.2 [I] Despliegue** · 25 min
  - Archivos: `README.md`.
  - Streamlit Community Cloud con `ANTHROPIC_API_KEY` en Secrets (design §14).
  - README de 10 líneas: qué es, cómo correr, URL del demo.
  - Probar la URL pública con el modo respaldo encendido y apagado.

- [ ] **T3.3 [P] Ensayo 2 en la URL pública** · 20 min
  - Guion completo con la API real. Si algún paso tarda más de 20 s, ese paso se hace en modo respaldo.

- [ ] **T3.4 [todos] Congelar a las 16:50**
  - Solo arreglos de errores. Último push. `pytest -q` en verde.

**Demo check 17:00:** URL + repositorio + demo + pitch.

---

## Orden de recorte

Si vamos atrasados, se recorta en este orden:

1. T3.1 Post-visita: el KPI queda en 2.2 y el pitch lo cuenta como siguiente paso.
2. T2.6 Respaldo genérico: el modo respaldo solo cubre C01.
3. Edición de montos en T2.3: se queda aprobar/rechazar.

**Nunca se recorta:** pipeline de C01, `check_policy`, contraoferta visible, aprobación humana y modo respaldo de C01.

---

## Guion del demo (3 min)

| Tiempo | Qué se muestra | Requisito |
|---|---|---|
| 0:00 – 0:30 | Problema: clientes con un solo producto. KPI de la barra lateral: 2.2 productos por cliente. | R8 |
| 0:30 – 0:50 | Agenda del día: C01 primero por potencial de venta cruzada. | R1 |
| 0:50 – 1:40 | "Preparar visita": Venta cruzada propone S/ 20,000 + seguro, Riesgo contraoferta S/ 12,000, Orquestador cierra. | R2, R3, R4 |
| 1:40 – 2:10 | El ejecutivo intenta subir a S/ 15,000: bloqueado. Deja 12,000 y aprueba. Sale la ficha. | R5, R6 |
| 2:10 – 2:35 | Nota de visita: "Aceptó ambos". CRM actualizado, KPI sube a 2.4. | R7, R8 |
| 2:35 – 3:00 | Business case: fórmula de utilidad incremental. Frase final. | – |

**Antes de salir a presentar:**

- [ ] "Reiniciar demo" pulsado.
- [ ] Segunda pestaña abierta con el modo respaldo encendido.
- [ ] En la laptop, `CROSSPILOT_FAKE_LLM=1 streamlit run app.py` listo por si falla el wifi.
- [ ] Nota de visita copiada en el portapapeles.

---

## Trazabilidad

| Requisito | Tareas | Tests |
|---|---|---|
| R1 Agenda | T1.4, T1.7 | `test_rules`: rank_clients |
| R2 Propuesta | T1.3, T1.6, T2.2 | `test_rules`: validate_offer |
| R3 Riesgo | T1.3, T2.1, T2.2 | `test_rules`: check_policy; `test_flow`: pipeline C01 |
| R4 Negociación | T2.2, T2.3 | `test_flow`: orden del log |
| R5 Aprobación | T2.3 | prueba manual de T2.3 |
| R6 Ficha | T1.6, T2.3 | prueba manual |
| R7 Post-visita | T3.1 | `test_rules`: validate_crm_entry; `test_flow`: flujo completo |
| R8 Indicadores | T1.2, T2.4, T3.1 | `test_flow`: 2.2 → 2.4 |
| R9 Respaldo | T1.5, T2.6 | todos los tests corren en fake |
| R10 Reinicio | T2.4 | prueba manual |
