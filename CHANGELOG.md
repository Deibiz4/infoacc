# Changelog - Sistema de Inteligencia Financiera y Trading (Infoacc)

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

---

## [2026-08-20] - Optimización Cuantitativa de Prompts y Sincronización del Hub

### 🚀 Añadido / Optimizado
- **Filtros Cuantitativos Mandatorios en Prompts Maestros:**
  - **Stocks (`report_generation_prompt.md`):** Incorporación de reglas basadas en el backtest histórico (6 años). Priorización de estrategias `VALUE_OVERSOLD` (+22.15 R) y `TREND_PULLBACK` (+20.14 R). Restricción estricta de cortos (`BREAKDOWN_SHORT` y `OVERBOUGHT_REJECTION`) a menos que el mercado general (SPY/QQQ) cotice bajo SMA 200 y VIX > 22.
  - **Crypto (`infocryptos/report_generation_prompt.md`):** Restricción de posiciones en corto (que acumularon -30.78 R en backtest) y enfoque prioritario en `MOMENTUM_TREND` (+17.48 R) sobre tokens de alta liquidez. Filtro de sobrecalentamiento de *Funding Rates*.
  - **Forex & Metales (`infofx/report_generation_prompt.md`):** Enfoque principal en `TREND_CONTINUATION` (+32.99 R, Win Rate 35.6%, Profit Factor 1.38) alineado con diferenciales de tipos y políticas de bancos centrales.
  - **Auditoría de Señales (`signal_review_prompt.md`):** Incorporación del protocolo de **Break-Even automático a +1.0 R / Target 1** e invalidación tras 3 sesiones sin activación.

- **Nuevos Informes y Escaneo Diario:**
  - Generación de informes del día 20 de agosto de 2026 para Acciones (`daily_market_report_2026_08_20.html`), Criptomonedas (`crypto_market_report_2026_08_20.html`) y Forex (`forex_market_report_2026_08_20.html`).
  - Sincronización de nuevas señales activas/pendientes: `COST`, `BA`, `DOGE`, `LTC`, `EURGBP`, `EURJPY`, `USDCHF`.

- **Web Hub y Analytics:**
  - Sincronización completa de los paneles HTML (`index.html`, `signals.html`, `analytics.html`) con la base de datos de señales y métricas de rendimiento.
  - Inclusión de `scratch/` en `.gitignore` para aislamiento de scripts de depuración.

---

## [2026-08-12] - Consolidación Multi-Mercado y Tracking de Rendimiento
- Integración de escaneo unificado en `master_workflow.py` para Acciones, Criptomonedas y Divisas.
- Implementación de `scripts/generate_analytics.py` para el cálculo automático de Win Rate, Profit Factor y curva de equity en R.
- Sincronización automática de histórico y señales activas con Google Sheets mediante API de Service Account.
- Soporte para variantes de entrada por pullback (*Stop-Hold*) y gestión de concentración máxima de riesgo por sector.

---

## [2026-07-16] - Lanzamiento Inicial de la Suite de Informes
- Arquitectura inicial con generadores HTML/Markdown institucionales (estilo Goldman Sachs / Blackstone).
- Escáner técnico con cálculo de SMA50, SMA200, RSI, ATR y volumen relativo.
- Pipeline automatizado de informes diarios y servidor web local.
