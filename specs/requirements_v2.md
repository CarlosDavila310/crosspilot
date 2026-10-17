# Crosspilot v2: cambios tras la mentoría

Este documento **reemplaza** lo que contradiga a `brief_y_spec_original.md`. Lo demás (datos §5, `check_policy` §6.1, `validate_offer` §6.3, agentes §7, modo respaldo §11) sigue igual.

## 1. Foco
Priorización de cartera y preparación de visita. La herramienta es un **apoyo, no una decisión automática**: el ejecutivo valida en terreno y aprueba.

## 2. Ejecución en paralelo (reemplaza R1.4/R2.1 "un clic por cliente")
- **V1.1** Al abrir la app (o con "Analizar cartera"), EL SISTEMA DEBE correr `run_pipeline` para los 10 clientes agendados **en paralelo** (`ThreadPoolExecutor(max_workers=10)`).
- **V1.2** Cada fila muestra su estado: En cola → Venta cruzada / Riesgo trabajando → listo, o error con botón "Reintentar".
- **V1.3** Barra de progreso global "Agentes analizando en paralelo · N/10".
- **V1.4** Si un agente falla en un cliente, solo esa fila queda en error; el resto sigue. Mensaje: "Riesgo no respondió" + Reintentar.

## 3. Puntaje único de prioridad (reemplaza el puntaje de rank_clients en la UI)
- **V2.1** Un solo número 0–100: **Prioridad de visita** = probabilidad de que el cliente adquiera más productos, con la oferta ya validada por Riesgo.
- **V2.2** Cálculo en código (`rules.priority_score`), nunca con el LLM:
  - `base` (relación con el banco) = 50·principalidad + 30·min(años_en_banco/10, 1) + 0.2·segmento
    (segmento: ingreso ≥ 4,000 → 100 "Pequeña empresa"; ≥ 2,500 → 70 "Micro · alta"; si no → 40 "Micro").
  - `oferta` = (min(100, margen_oferta_final/10)·0.5 + prob_máx_recomendación·0.3 + n_items/2·20) × (0.6 si atraso > 15 días).
    Sin oferta viable → 5.
  - `prioridad` = round(0.4·base + 0.6·oferta).
- **V2.3** La UI **no** muestra base ni oferta por separado: solo el puntaje final.
- **V2.4** Semáforo: verde `#1E9E5A` si > 80, ámbar `#F2B134` si 60–80, rojo `#C62828` si < 60. Sin texto "Alta/Media/Baja".
- **V2.5** Orden de la tabla: analizados por prioridad desc; pendientes al final.
- Test: con el seed, C01 queda #1 (prioridad 85).

## 4. Tabla de cartera (pantalla principal)
Columnas: Orden · Cliente (nombre + negocio) · Productos actuales (chips) · Oferta de venta cruzada tras riesgo · Prioridad de visita · Estado.
- En "Oferta", **un producto por línea con su etiqueta al lado** (APROBADO / CONTRAOFERTA / VETO). Contraoferta muestra el monto ajustado; veto, el propuesto.
- Estado: Por aprobar · Aprobada · Rechazada · Sin oferta.
- Clic en fila → panel de detalle.

## 5. Panel de detalle del cliente
1. **Oferta** (mensaje de cierre del Orquestador arriba):
   - Productos recomendados por la IA **sombreados** (`#EAF4F2`, etiqueta "RECOMENDADO POR IA"). Agregados por el ejecutivo en blanco ("Agregado por ti").
   - Cada producto: botón quitar. Créditos: monto editable paso S/ 500, con "Máximo permitido".
   - Botón "+ Agregar producto" → **popup** con dos listas: Del banco / De aliados. Créditos no elegibles no se pueden agregar.
   - Cliente "Sin oferta viable": también puede agregar, **solo productos sin crédito** (ahorro, seguros, QR, aliados).
   - Caja **Comentarios** antes de aprobar/rechazar. Se guarda con la decisión (para análisis posterior).
   - Aprobar: revalida con `check_policy`; máximo un crédito; error bloquea y explica. Rechazar: sin ficha.
2. **Chat en dos pestañas**: Venta cruzada y Riesgo (`st.tabs` + `st.chat_message` + `st.chat_input`). Mensaje inicial = salida del agente. El ejecutivo pregunta o corrige; Riesgo nunca cambia la decisión de la regla. Sugerencias rápidas por pestaña.
3. **Ficha de visita** tras aprobar (agente Visita, §7.4 original).
4. **Perfil del cliente**: años en banco y en sistema, principalidad, mora 12m + calificación SBS (≤8 Normal, ≤30 CPP, >30 Deficiente), histórico de deuda 24m (banco vs otras), ahorro 24m, atraso por mes, productos del banco (tiene/elegible/no elegible), línea de tiempo, intereses y productos con alta probabilidad (banco + ecosistema).

## 6. Barra lateral
Título, Modo respaldo, Productos por cliente (2.2 → proyectado si aceptan lo aprobado), Clientes analizados N/10, Ofertas aprobadas, Vetos de riesgo, Reiniciar demo, **lista general "Productos para ofrecer"** (del banco y de aliados, independiente del cliente), nota "Próximo módulo: registro post-visita (en evolución)".

## 7. Datos nuevos (sintéticos, en `data/seed.json`)
Por cliente: `bank_since`, `system_since`, `principality` (0–1), `savings_balance`, `product_since` {product_id: "AAAA-MM"}, `interests` [str], `recommendations` [{brand, product, prob, why}]. Valores exactos: ver `PROFILE` en `design/Crosspilot v2.dc.html`.
Catálogo de aliados (`type: "aliado"`, no pasa por riesgo de crédito): Seguro multirriesgo Pyme, Seguro vehicular, Seguro de salud para emprendedores (Pacífico Seguros); Cobros con Yape para negocio (Yape); Fondo de inversión de corto plazo (Tyba). Mostrar aviso "Aliados de ejemplo, sin acuerdo comercial".

## 8. Fuera del core
Post-visita y CRM (R7) quedan como módulo futuro. No mostrar campo de nota post-visita en la pantalla principal.

## 9. Tareas nuevas (sobre tasks.md original)
- **T2.8 [D]** `priority_score` + datos de perfil y aliados en seed. Test: C01 = 85 y #1.
- **T2.9 [A]** `run_portfolio(state)` paralelo con ThreadPoolExecutor; errores por cliente aislados. Test en fake.
- **T2.10 [I]** Tabla de cartera + semáforo + progreso.
- **T2.11 [I]** Panel de detalle (`@st.dialog` o página): oferta editable, popup agregar, comentarios, chat en pestañas, ficha, perfil con `st.bar_chart` / `st.line_chart`.
- **T2.12 [A]** Chat de seguimiento: `run_agent` con historial por cliente y pestaña; modo respaldo con respuestas por palabra clave (ver `answer()` en el diseño).
