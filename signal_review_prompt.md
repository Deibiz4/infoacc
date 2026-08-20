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

**Lógica de Actualización Cuantitativa:**
Para cada señal con estado "PENDING" o "ACTIVE":
*   **PENDING -> ACTIVE:** Si el precio tocó el `entry_price`.
*   **ACTIVE -> HIT_TARGET:** Si el precio tocó el `target_price` o TP2 (resultado: +2.5R a +3.0R).
*   **ACTIVE -> HIT_STOP:** Si el precio tocó el `stop_loss` (resultado: -1.0R o 0.0R si ya estaba en Break-Even).
*   **ACTIVE (Gestión Break-Even):** Si el precio alcanzó el 50% del recorrido hacia el target (+1.0R), marcar nota `[SL movido a Break-Even]` para proteger el capital.
*   **PENDING -> EXPIRED:** Si han pasado 3 días de mercado sin activar la zona de entrada.

**Salida Requerida:**

1.  **JSON Actualizado:** Devuelve el bloque de código JSON completo con los estados, `r_result` y notas actualizadas (ej. "TP1 alcanzado (+1.5R) y SL en BE", "Stop hit (-1.0R)").

2.  **Resumen de Rendimiento (Markdown):**
    Genera un bloque de métricas para el informe diario:
    
    ### 🚦 Rendimiento Cuantitativo de Señales (Últimos 7 Días)
    *   **✅ Targets Alcanzados (+R):** [Lista de Tickers y R ganado]
    *   **❌ Stops Saltados (-R):** [Lista de Tickers y R perdido]
    *   **🛡️ En Break-Even (+0R protegido):** [Lista de Tickers con capital protegido]
    *   **⏳ Operaciones Activas:** [Lista de Tickers y R flotante]
    *   **📊 Balance R Neto (7D):** `+X.X R`
    *   **Comentario Institucional:** [Diagnóstico de 1 línea]

**Ejecución:**
Aquí tienes el JSON actual y los precios de hoy. Procesa la actualización:

[JSON ACTUAL AQUÍ]
[PRECIOS ACTUALES AQUÍ]
```
