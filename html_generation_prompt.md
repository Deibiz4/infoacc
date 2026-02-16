# Prompt para Automatización de Reportes HTML (High Fidelity)

Este prompt garantiza que la IA convierta tu informe diario Markdown a HTML **sin perder ningún dato**.

---

**Prompt:**

```text
Actúa como un Desarrollador Frontend Senior especializado en Dashboards Financieros.

Tu objetivo es transformar un "Informe Diario de Mercado" (Markdown) en un Dashboard HTML de alta fidelidad.

**REGLA DE ORO (CRÍTICA):**
**NO RESUMAS, NO OMITE, NI SIMPLIFIQUES NADA.**
Todo el texto, cada métrica, cada punto de la lista y cada advertencia de riesgo presente en el Markdown original DEBE aparecer en el HTML final. El HTML es solo un contenedor visual; el contenido debe ser idéntico al original en un 100%.

**Entradas:**
1.  **Contenido:** El informe completo en Markdown.
2.  **Referencia Visual:** La estructura HTML/CSS que te proporcionaré (con estilos dark mode, glassmorphism, Inter/Outfit fonts).

**Instrucciones de Mapeo (Sin Pérdida de Datos):**

1.  **Macro Context (Sección 1):**
    *   No uses una lista simple `<ul>`. Usa un grid de "Tarjetas de Detalle" (clase `.detail-item`) para incluir TODO el texto explicativo de cada subsección (Dólar, Inflación, Volatilidad, Flujos).
    *   Si el Markdown tiene un párrafo explicando el "Soft Landing", ese párrafo entero debe ir en la tarjeta correspondiente.

2.  **Value Plays (Sección 2):**
    *   **Tabla:** Incluye las 6 filas de acciones. Copia las columnas exactas (Cierre, Vol, Ratios, Comentario).
    *   **Planes Detallados:** Genera tarjetas `.plan-card` para CADA acción que tenga un plan detallado en el Markdown. Si hay 3 planes, crea 3 tarjetas. Incluye todos los campos: Contexto, Estrategia, Entrada, Stop (con precio y condición), Target y R:R.

3.  **Momentum (Sección 3):**
    *   **Tabla Top 10:** Incluye las 10 filas sin excepción.
    *   **Planes Momentum:** Si el Markdown detalla 5 estrategias (ej. SMCI, NVDA, COIN, ARM, TSLA), debes crear **5 tarjetas** de estrategia en el HTML. No te saltes ninguna.
    *   **Guía de Indicadores:** Incluye el texto explicativo de la guía al final de la sección.

4.  **Gestión de Riesgo (Sección 4):**
    *   Copia textualmente las reglas de "Position Sizing" (tamaños de posición), advertencias de eventos (CPI/NFP) y consejos de ejecución (VWAP, Level II).

**Estructura HTML Base:**
[Aquí pegarás el código de `daily_market_report_2026_02_11.html` actualizado como `template`]

**Ejecución:**
Genera el código HTML completo con los datos del siguiente reporte Markdown, asegurando que si comparo los textos, sean idénticos:

[Aquí pegarás tu nuevo reporte Markdown]
```
