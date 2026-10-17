# Crosspilot: requisitos

## 1. Contexto

Muchos clientes de un banco de microfinanzas tienen un solo producto. Cada uno es ingreso que se queda
en la mesa: el ejecutivo no sabe qué ofrecer ni cuándo, no tiene tiempo para preparar la oferta, y
muchas ofertas terminan rechazadas por riesgo o sobreendeudan al cliente.

Crosspilot es un equipo de agentes que ayuda al ejecutivo a **vender más productos a sus clientes
actuales, sin perder el control del riesgo**. La métrica que importa es **productos por cliente**.

Restricciones: se construye en un día, con 4 personas, y se demuestra en vivo en 3 minutos.

## 2. Usuarios

- **Ejecutivo de negocios:** usuario único de la app. Prepara visitas, aprueba ofertas, registra resultados.
- **Jurado:** mira el demo y puede abrir la URL. No es usuario del flujo.

## 3. Glosario

| Término | Significado |
|---|---|
| Venta cruzada | Ofrecer a un cliente actual un producto que todavía no tiene. |
| Capacidad disponible | Deuda adicional que el cliente puede asumir según la política. |
| Contraoferta | Oferta de crédito ajustada al monto máximo que permite la política. |
| Veto | Producto que Riesgo rechaza sin contraoferta posible. |
| Ficha de visita | Resumen de una página que el ejecutivo lee antes de visitar al cliente. |
| CRM simulado | Lista en memoria de los resultados de visita de la sesión. |

## 4. Requisitos funcionales

Formato EARS. Cada criterio tiene un ID que usan las tareas y los tests.

### R1. Agenda priorizada

- **R1.1** CUANDO el ejecutivo abre la app, EL SISTEMA DEBE mostrar los 5 clientes con mayor potencial
  de venta cruzada, ordenados de mayor a menor.
- **R1.2** El potencial DEBE calcularse en código con `rank_clients` (ver diseño §6.2), nunca con el LLM.
- **R1.3** Cada fila DEBE mostrar nombre, negocio, productos actuales, productos elegibles y puntaje.
- **R1.4** EL SISTEMA DEBE permitir elegir cualquier cliente de la cartera, no solo los 5 de la agenda.

### R2. Propuesta de venta cruzada

- **R2.1** CUANDO el ejecutivo elige un cliente y pulsa "Preparar visita", el agente Venta cruzada DEBE
  proponer 1 o 2 productos del catálogo que el cliente no tenga.
- **R2.2** Cada producto propuesto DEBE incluir una razón basada en las señales del cliente.
- **R2.3** Los productos de crédito DEBEN incluir monto en soles; los demás, sin monto.
- **R2.4** EL SISTEMA DEBE descartar en código, y registrar en la conversación el motivo, todo producto
  inexistente, ya contratado, de crédito sin monto válido, o cualquier crédito después del primero.
- **R2.5** SI no queda ningún producto válido, EL SISTEMA DEBE mostrar "Sin oferta viable" y no seguir.

### R3. Revisión de riesgo

- **R3.1** Cada producto propuesto DEBE evaluarse con `check_policy` (diseño §6.1).
- **R3.2** SI un crédito excede la capacidad disponible y el máximo permitido alcanza el monto mínimo del
  producto, EL SISTEMA DEBE contraofertar con el máximo permitido.
- **R3.3** SI el cliente tiene más de 15 días de atraso máximo en 12 meses, o el máximo permitido es
  menor que el monto mínimo del producto, EL SISTEMA DEBE vetar el crédito.
- **R3.4** Los productos que no son crédito DEBEN aprobarse si el cliente no los tiene.
- **R3.5** La decisión (aprobado, contraoferta, veto) y el monto DEBEN venir de `check_policy`. El agente
  Riesgo solo redacta la explicación; si su texto contradice la regla, gana la regla.

### R4. Negociación visible

- **R4.1** EL SISTEMA DEBE mostrar el intercambio entre agentes como mensajes en orden, con remitente
  visible: VENTA CRUZADA, RIESGO, ORQUESTADOR.
- **R4.2** El Orquestador DEBE cerrar la negociación con un mensaje que diga qué se acepta, qué cambia y
  qué se descarta.

### R5. Aprobación humana

- **R5.1** Ninguna oferta DEBE pasar a "aprobada" sin que el ejecutivo pulse "Aprobar".
- **R5.2** El ejecutivo DEBE poder quitar productos y editar montos de crédito antes de aprobar.
- **R5.3** CUANDO el ejecutivo edita un monto, EL SISTEMA DEBE revalidarlo con `check_policy` al aprobar;
  SI no pasa, DEBE bloquear la aprobación y mostrar el motivo.
- **R5.4** El ejecutivo DEBE poder rechazar la oferta; en ese caso no se genera ficha.

### R6. Ficha de visita

- **R6.1** CUANDO la oferta se aprueba, el agente Visita DEBE generar una ficha con: resumen del cliente,
  oferta final, 3 puntos de conversación, 2 objeciones probables con respuesta y siguiente paso.
- **R6.2** La ficha NO DEBE cambiar productos ni montos aprobados.

### R7. Registro post-visita

- **R7.1** CUANDO el ejecutivo escribe la nota de la visita y pulsa "Registrar", el agente Post-visita
  DEBE convertirla en un registro de CRM: resultado, productos aceptados, siguiente acción, fecha de
  seguimiento y resumen.
- **R7.2** Los productos aceptados DEBEN ser un subconjunto de la oferta aprobada; la fecha DEBE tener
  formato `AAAA-MM-DD` y no ser anterior a hoy. SI no cumple, EL SISTEMA DEBE mostrar error y no guardar.
- **R7.3** CUANDO hay productos aceptados, EL SISTEMA DEBE agregarlos a los productos del cliente.

### R8. Indicadores

- **R8.1** EL SISTEMA DEBE mostrar siempre: productos por cliente (promedio de la cartera), ofertas
  aprobadas, productos aceptados y vetos de riesgo, de la sesión actual.
- **R8.2** Productos por cliente DEBE actualizarse al registrar una visita con productos aceptados.

### R9. Modo respaldo

- **R9.1** CUANDO `CROSSPILOT_FAKE_LLM=1` o el interruptor "Modo respaldo" está activo, EL SISTEMA DEBE
  usar respuestas predefinidas y no llamar a la API.
- **R9.2** SI una llamada a la API falla, EL SISTEMA DEBE mostrar qué agente falló y sugerir activar el
  modo respaldo, sin perder el estado de la sesión.

### R10. Reinicio del demo

- **R10.1** CUANDO el ejecutivo pulsa "Reiniciar demo", EL SISTEMA DEBE volver al estado inicial del
  `seed.json` y limpiar la visita en curso y los indicadores.

## 5. Requisitos no funcionales

- **NF1** Flujo completo de un cliente (propuesta, riesgo y negociación) en menos de 45 s con la API real.
- **NF2** Solo datos sintéticos. Ningún dato real de clientes en el repo ni en los prompts.
- **NF3** La API key nunca se escribe en el repo ni se muestra en la UI.
- **NF4** Estado aislado por sesión de navegador.
- **NF5** Dependencias de ejecución: solo `streamlit` y `anthropic`.
- **NF6** Los tests corren sin red y sin API key.
- **NF7** Interfaz en español, legible en una pantalla de proyector.

## 6. Fuera de alcance

Autenticación, datos o sistemas reales del banco, persistencia entre reinicios, varios ejecutivos,
transcripción de audio (la nota se escribe en texto), app móvil, integración con NANDA Town.

## 7. Criterios de éxito del demo

1. El cliente C01 recorre todo el flujo en vivo: propuesta de S/ 20,000, contraoferta de S/ 12,000,
   aprobación, ficha y registro en CRM.
2. Productos por cliente sube de 2.2 a 2.4 al final del demo.
3. El mismo flujo funciona en modo respaldo, sin red.
