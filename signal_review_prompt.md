# Prompt de Revisión de Señales y Rendimiento

Este prompt está diseñado para que una IA analice el rendimiento de las señales de trading pasadas basándose en los precios actuales del mercado.

---

**Prompt:**

```text
Actúa como un Auditor de Trading Cuantitativo.

Tu tarea es revisar el archivo de historial de señales (`data/signals.json`) y actualizar el estado de cada operación basándote en los precios actuales del mercado que te proporcionaré.

**Entradas:**
1.  **Historial:** Contenido actual de `data/signals.json`.
2.  **Precios Actuales:** Una lista de precios actuales (High, Low, Close) para los tickers monitorizados (proporcionada por el usuario).

**🚨 REGLA DE INTEGRIDAD DE PRECIOS:**
*   Usa **SOLAMENTE** precios reales de mercado para verificar las señales.
*   Si un precio en el JSON histórico parece una alucinación (ej. NVDA $700 vs Real $180), **IGNORA EL DATO HISTÓRICO Y USA EL PRECIO REAL** para el cálculo de PnL y estado.
*   Reporta cualquier discrepancia mayor al 20% en las notas de la señal.

**Lógica de Actualización:**
Para cada señal con estado "PENDING" o "ACTIVE":
*   **PENDING -> ACTIVE:** Si el precio tocó el `entry_price`.
*   **ACTIVE -> HIT_TARGET:** Si el precio tocó el `target_price`.
*   **ACTIVE -> HIT_STOP:** Si el precio tocó el `stop_loss`.
*   **PENDING -> EXPIRED:** Si han pasado 3 días sin activar entrada.

**Salida Requerida:**

1.  **JSON Actualizado:** Devuelve el bloque de código JSON completo con los estados y notas actualizadas (ej. "Stop hit en apertura", "Target alcanzado en 24h").

2.  **Resumen de Rendimiento (Markdown):**
    Genera un breve bloque de texto para incluir en el próximo informe, con el siguiente formato:
    
    ### 🚦 Rendimiento de Señales Recientes (7 Días)
    *   **✅ Aciertos:** [Lista de Tickers que tocaron Target]
    *   **❌ Stops:** [Lista de Tickers que tocaron Stop]
    *   **⏳ Activas:** [Lista de Tickers en juego]
    *   **Comentario:** [Breve análisis de 1 línea, ej. "Alta volatilidad activó stops en Tech, pero Value funcionó bien."]

**Ejecución:**
Aquí tienes el JSON actual y los precios de hoy. Procesa la actualización:

[JSON ACTUAL AQUÍ]
[PRECIOS ACTUALES AQUÍ]
```
