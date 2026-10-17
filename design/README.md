# Handoff: Crosspilot v2 (priorización y pre-visita)

## Overview
Pantalla única de Streamlit para el ejecutivo de negocios: cartera del día analizada en paralelo por agentes, puntaje único de prioridad con semáforo, y panel por cliente para gestionar/aprobar la oferta, conversar con los agentes y ver el perfil.

## About the Design Files
`Crosspilot v2.dc.html` es una **referencia de diseño en HTML** (prototipo interactivo), no código para copiar. La tarea es **recrearlo en Streamlit** (`app.py`) con componentes nativos + CSS ligero vía `st.markdown(..., unsafe_allow_html=True)`. Ábrelo en un navegador para ver el comportamiento. La lógica JS del archivo (`check`, `pipeline`, `i1Of`, `i2Of`, `buildDetail`, `answer`) sirve de referencia exacta para `rules.py` y `fakes.py`.

## Fidelity
**Alta fidelidad**: colores, tipografía, copy y comportamiento finales. Donde Streamlit no llegue, prioriza comportamiento y copy sobre píxeles.

## Screens / Views
### 1. Principal
- **Layout**: sidebar fijo (fondo `#0F2A2E`, ~270 px) + contenido (máx 1240 px, padding 32/40 px).
- **Encabezado**: "Sábado 17 de octubre · 10 clientes agendados" (16 px, `#4A6572`); título "Cartera priorizada del día" (Cambria 38 px bold); subtítulo "Prioridad de visita: probabilidad de que el cliente adquiera más productos, con la oferta ya validada por Riesgo."; a la derecha progreso + botón "Analizar cartera".
- **Tabla**: cabecera `#F4FAF8`, 13 px mayúsculas `#4A6572`; filas con borde `#D7E7E3`, hover `#F4FAF8`.
  - Orden: círculo 30 px; top 3 `#0B4F57` texto blanco, resto `#EEF2F3`.
  - Productos actuales: chips 14 px, fondo `#EEF2F3`.
  - Oferta: una línea por producto, nombre 15 px bold + etiqueta 11 px bold blanca (APROBADO `#007F73`, CONTRAOFERTA `#C2410C`, VETO `#7A1A12`). En análisis: "Venta cruzada" (✓ o spinner) y "Riesgo" (spinner).
  - Prioridad: píldora con círculo 26 px de color semáforo + número Cambria 28 px. Fondo píldora: verde `#E3F4EA`, ámbar `#FDF1D6`, rojo `#FBE4E4`.
  - Estado: Por aprobar (`#F2B134`/texto oscuro), Aprobada (`#007F73`), Rechazada (`#4A6572`), Sin oferta (`#EEF2F3`).
- Nota inferior: "El puntaje es un apoyo, no una decisión: el ejecutivo valida en terreno y aprueba cada oferta."

### 2. Panel de detalle (drawer derecho, máx 1140 px; en Streamlit: `@st.dialog` ancho grande o página)
- Header `#0F2A2E`: nombre (Cambria 28), "C01 · negocio · distrito · Ingreso neto S/ X/mes" (`#8FD3C4`), píldora "Prioridad 85 · #1" (`#8FD3C4`).
- **Oferta** (borde 2 px `#F2B134`): banda Orquestador `#0B4F57`; ítems IA fondo `#EAF4F2` borde `#B5D3CC` + "RECOMENDADO POR IA"; ítems manuales blancos; quitar (papelera); monto con −/+ paso 500, borde naranja y "Supera el máximo" si excede; "+ Agregar producto" (borde discontinuo teal) abre popup; caja Comentarios; error `#FCEEE7` borde `#C2410C` "No se puede aprobar"; botones Aprobar (teal) / Rechazar (contorno gris).
- **Chat**: pestañas Venta cruzada (teal) / Riesgo (naranja), burbujas agente `#EAF4F2` / `#FCEEE7`, usuario `#FDF1D6`; chips de preguntas; input + enviar.
- **Popup Agregar producto**: dos columnas "DEL BANCO" / "DE ALIADOS", cada fila con estado (Ya lo tiene / En la oferta / + Agregar), créditos con "Hasta S/ X" o "No elegible hoy", aliados con "Afinidad X%".
- **Ficha de visita** (tras aprobar) y **Perfil del cliente** (ver requirements_v2 §5).

## Interactions & Behavior
- Análisis automático al cargar; tiempos escalonados por cliente; el orden se recalcula al terminar cada uno.
- Esc cierra popup, luego panel.
- Aprobar: ≥1 producto, máx 1 crédito, cada crédito `check_policy` ok; si no, error y no cambia estado. Luego "El agente Visita está preparando la ficha…".
- Simular fallo: C05 → "Riesgo no respondió" + Reintentar (funciona con Modo respaldo).

## State Management
`runs[cid] = {status: idle|running|done|error, vc: bool, res}`; `decisions[cid] = {status: PENDIENTE|SIN_OFERTA|APROBADA|RECHAZADA, list:[pid], edits:{pid:{amount}}, limited: bool, errors, comment, approved, brief}`; `chats[cid] = {VC:[], RISK:[]}`; `detail`, `tab`, `addOpen`, `fallback`.

## Design Tokens
Colores: fondo oscuro `#0F2A2E`, teal profundo `#0B4F57`, teal `#007F73`, menta `#8FD3C4`, tarjeta `#EAF4F2`, ámbar `#F2B134`, ámbar claro `#FDF1D6`, naranja riesgo `#C2410C`, naranja claro `#FCEEE7`, veto `#7A1A12`, gris azulado `#4A6572`, bordes `#D7E7E3` / `#B5D3CC`, neutro `#EEF2F3`, semáforo `#1E9E5A` / `#F2B134` / `#C62828`.
Tipografía: títulos Cambria (fallback Caladea/Georgia), texto Calibri (fallback Carlito/Segoe UI). Base 17 px; títulos 21–38 px; etiquetas 11–14 px bold. Radios: 10 px tarjetas, 6–8 px chips/botones. Sin sombras fuertes.

## Assets
Iconos Font Awesome 6 (diagram-project, bullseye, shield-halved, user-tie, trash-can, wand-magic-sparkles). En Streamlit: emojis 🧭 🎯 🛡️ 👤 como avatares. Sin imágenes.

## Files
- `Crosspilot v2.dc.html`: prototipo completo (plantilla + lógica en el mismo archivo).
