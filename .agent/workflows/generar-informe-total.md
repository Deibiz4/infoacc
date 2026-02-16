---
description: Genera el informe COMPLETO con análisis IA (Stocks, Crypto y Forex)
---

# 🤖 Flujo Maestro de Inteligencia de Mercado

Este workflow combina la automatización de datos con el análisis experto de la IA.

### Paso 1: Recolección de Datos Reales (Automatizado)
// turbo
1. Ejecuta el escaneo y actualización de hojas de cálculo en modo datos:
   `python d:\Docker\infoacc\master_workflow.py --data-only`

### Paso 2: Análisis IA Secuencial (Intervención de Antigravity)
El Agente leerá los archivos `signals.json` y generará los informes siguiendo el **`report_generation_prompt.md`**:

1. 📈 **STOCKS**: Generar `reports/daily_market_report_[today].html` y `.md` con análisis Goldman Sachs/Blackstone.
2. ₿ **CRYPTO**: Generar `infocryptos/reports/crypto_market_report_[today].html` y `.md` con métricas on-chain.
3. 💱 **FOREX**: Generar `infofx/reports/forex_market_report_[today].html` y `.md` con análisis DXY/Macro.

### Paso 3: Sincronización del Hub
1. Una vez generados los informes, el Agente ejecutará los scripts de actualización del Hub para cada mercado:
   - `python d:\Docker\infoacc\scripts\update_hub.py`
   - `python d:\Docker\infoacc\infocryptos\scripts\update_hub.py`
   - `python d:\Docker\infoacc\infofx\scripts\update_hub.py`

### Paso 4: Veredicto Final
El Agente presentará un resumen ejecutivo de las 3 señales con mayor convicción del día.
