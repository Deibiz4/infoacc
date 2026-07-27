import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

import json
import datetime
import os
import random

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

# --- CSS STYLES (From Feb 14 Report) ---
CSS_STYLES = """
    :root {
        --bg-color: #0f172a;
        --card-bg: rgba(30, 41, 59, 0.7);
        --glass-border: 1px solid rgba(255, 255, 255, 0.1);
        --accent-color: #10b981;
        --text-primary: #e2e8f0;
        --text-secondary: #94a3b8;
        --success: #10b981;
        --danger: #ef4444;
        --warning: #f59e0b;
    }

    body {
        font-family: 'Inter', sans-serif;
        background-color: var(--bg-color);
        color: var(--text-primary);
        margin: 0;
        padding: 20px;
        line-height: 1.6;
        background-image: radial-gradient(circle at top right, #1e293b 0%, transparent 40%);
    }

    h1, h2, h3 {
        font-family: 'Outfit', sans-serif;
        color: white;
        margin-top: 0.5em;
    }

    h1 { font-size: 2.5rem; text-align: center; margin-bottom: 2rem; text-shadow: 0 0 20px rgba(59, 130, 246, 0.5); }
    h2 { font-size: 1.75rem; border-bottom: 1px solid var(--text-secondary); padding-bottom: 0.5rem; margin-top: 3rem; color: var(--accent-color); }
    h3 { font-size: 1.25rem; color: #cbd5e1; }

    .container {
        max-width: 1200px;
        margin: 0 auto;
    }

    .card {
        background: var(--card-bg);
        backdrop-filter: blur(12px);
        border: var(--glass-border);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    .details-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 1.5rem;
    }

    .metric-value { font-size: 1.5rem; font-weight: 700; color: white; display: block; margin-bottom: 0.5rem; }
    .metric-context { font-size: 0.9rem; color: var(--text-secondary); }

    .positive { color: var(--success); }
    .negative { color: var(--danger); }

    .plan-card {
        border-left: 4px solid var(--accent-color);
        background: linear-gradient(90deg, rgba(59,130,246,0.1) 0%, transparent 100%);
    }

    .plan-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1.5rem;
    }

    .plan-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }

    .plan-price { font-size: 1.1em; font-weight: bold; }

    .risk-reward {
        background: rgba(16, 185, 129, 0.1);
        color: var(--success);
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.8em;
        font-weight: bold;
    }

    .trade-levels {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
        margin-top: 1rem;
        font-size: 0.9em;
    }

    .level-label { color: var(--text-secondary); display: block; margin-bottom: 0.2rem; }
    .level-value { color: white; font-weight: 600; }

    .entry { border-left: 2px solid var(--accent-color); padding-left: 0.5rem; }
    .stop { border-left: 2px solid var(--danger); padding-left: 0.5rem; }
    .target { border-left: 2px solid var(--success); padding-left: 0.5rem; }

    ul { list-style-type: none; padding: 0; }
    li { margin-bottom: 0.5rem; padding-left: 1.2rem; position: relative; }
    li::before { content: "•"; color: var(--accent-color); position: absolute; left: 0; font-weight: bold; }

    .footer {
        text-align: center;
        margin-top: 4rem;
        color: var(--text-secondary);
        font-size: 0.8rem;
        border-top: 1px solid rgba(255,255,255,0.1);
        padding-top: 2rem;
    }
    
    .badge {
        font-size: 0.7em; 
        padding: 2px 6px; 
        border-radius: 4px; 
        vertical-align: middle; 
        color: #000; 
        font-weight: bold;
    }
"""

def fetch_macro_data():
    """Fetches VIX and 10Y Yield from yfinance."""
    macro = {
        "vix": "N/A", "vix_change": "", "vix_color": "var(--text-primary)",
        "tnx": "N/A", "tnx_change": "",
        "dxy": "N/A", "dxy_change": ""
    }
    
    if not YFINANCE_AVAILABLE:
        return macro

    try:
        tickers = ["^VIX", "^TNX", "DX-Y.NYB"]
        data = yf.download(tickers, period="5d", progress=False)['Close']
        
        # Helper to get value and percent change
        def get_val_change(ticker):
             try:
                if ticker in data.columns:
                    series = data[ticker].dropna()
                elif ticker in data.index: # Transposed sometimes
                     series = data.loc[ticker].dropna()
                else:
                    return None, None
                
                if len(series) < 2: return series.iloc[-1], 0
                
                curr = series.iloc[-1]
                prev = series.iloc[-2]
                pct_change = ((curr - prev) / prev) * 100
                return curr, pct_change
             except: return None, None

        # VIX
        vix_val, vix_pct = get_val_change("^VIX")
        if vix_val:
            macro["vix"] = f"{vix_val:.2f}"
            macro["vix_change"] = f"{vix_pct:+.2f}%"
            if vix_val > 20: macro["vix_color"] = "var(--danger)"
            elif vix_val < 15: macro["vix_color"] = "var(--success)"
            
        # TNX
        tnx_val, tnx_pct = get_val_change("^TNX")
        if tnx_val:
             macro["tnx"] = f"{tnx_val:.2f}%"
             macro["tnx_change"] = f"{tnx_pct:+.2f}%"

        # DXY
        dxy_val, dxy_pct = get_val_change("DX-Y.NYB")
        if dxy_val:
             macro["dxy"] = f"{dxy_val:.2f}"
             macro["dxy_change"] = f"{dxy_pct:+.2f}%"

    except Exception as e:
        print(f"⚠️ Error fetching macro data: {e}")
        
    return macro

def generate_signal_card(signal, is_momentum=False):
    ticker = signal.get("ticker")
    price = signal.get("entry_price")

    # Forex precision (5 decimals for pipettes)
    entry = f"{price:.5f}"
    stop = f"{signal.get('stop_loss'):.5f}"
    target = f"{signal.get('target_price'):.5f}"
    notes = signal.get("notes")
    direction = signal.get("type", "LONG").upper()
    context = signal.get("context", "")

    # Calculate R:R (handles both LONG and SHORT)
    try:
        risk = abs(price - signal.get("stop_loss"))
        reward = abs(signal.get("target_price") - price)
        rr_ratio = reward / risk if risk > 0 else 0
        rr_text = f"1:{rr_ratio:.1f}"
    except:
        rr_text = "N/A"

    # Direction badge and card border
    if direction == "SHORT":
        dir_badge_style = "background: var(--danger); color: white;"
        card_border = "border-left: 4px solid var(--danger);"
        dir_icon = "&#9660; SHORT"
        rr_color = "var(--danger)"
    else:
        dir_badge_style = "background: var(--success); color: white;"
        card_border = "border-left: 4px solid var(--success);"
        dir_icon = "&#9650; LONG"
        rr_color = "var(--success)"

    context_label = context.replace("_", " ").title()

    html = f"""
            <div class="card plan-card" style="{card_border}">
                <div class="plan-header">
                    <div style="display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap;">
                        <h3 style="margin:0;">{ticker}</h3>
                        <span style="{dir_badge_style} font-size:0.75rem; font-weight:700; padding:3px 10px; border-radius:20px; letter-spacing:0.05em;">{dir_icon}</span>
                        <span style="background:rgba(255,255,255,0.08); color:var(--text-secondary); font-size:0.7rem; font-weight:600; padding:2px 8px; border-radius:12px;">{context_label}</span>
                    </div>
                    <span class="plan-price">{entry}</span>
                </div>
                <p class="metric-context">{notes}</p>
                <div class="trade-levels">
                    <div class="entry">
                        <span class="level-label">Entry</span>
                        <span class="level-value">{entry}</span>
                    </div>
                    <div class="stop">
                        <span class="level-label">Stop Loss</span>
                        <span class="level-value">{stop}</span>
                    </div>
                    <div class="target">
                        <span class="level-label">Target</span>
                        <span class="level-value">{target}</span>
                    </div>
                </div>
                <div style="margin-top: 1rem; text-align: right;">
                    <span class="risk-reward" style="background: {rr_color}20; color: {rr_color}; border: 1px solid {rr_color}40;">R:R {rr_text}</span>
                </div>
            </div>
    """
    return html

def generate_risk_section():
    weekday = datetime.datetime.now().strftime("%A")
    warning = ""
    if weekday == "Friday":
        warning = "<li><strong>Cierre Semanal:</strong> El mercado de divisas cierra los viernes. Evita dejar posiciones abiertas durante el fin de semana para prevenir gaps.</li>"
    
    html = f"""
    <section>
        <h2>4. Gestión de Riesgo Forex</h2>
        <div class="card" style="border-left: 4px solid var(--accent-color);">
            <ul>
                <li><strong>Leverage Safety:</strong> Limit leverage to maximum 1:10 - 1:20 to prevent margin calls.</li>
                <li><strong>Pip Risk:</strong> Ensure Stop Loss distance is strictly within 1-2% account equity risk.</li>
                <li><strong>Macro News:</strong> Avoid trading during NFP, FOMC, or CPI events if you cannot manage high volatility.</li>
                <li><strong>DXY Correlation:</strong> Always monitor the US Dollar Index; it is the primary engine of major pairs.</li>
                <li><strong>Stop Loss:</strong> Mandatory. Liquidity can vanish during unforeseen events.</li>
            </ul>
        </div>
    </section>
    """
    return html

def generate_html_report(signals, macro):
    today_str = datetime.datetime.now().strftime("%B %d, %Y")

    # Split by direction
    long_signals = [s for s in signals if s.get("type", "LONG").upper() == "LONG"]
    short_signals = [s for s in signals if s.get("type", "LONG").upper() == "SHORT"]

    long_cards_html = "".join([generate_signal_card(s, False) for s in long_signals])
    short_cards_html = "".join([generate_signal_card(s, False) for s in short_signals])

    if not long_cards_html:
        long_cards_html = "<p class='metric-context'>No LONG forex opportunities identified today.</p>"
    if not short_cards_html:
        short_cards_html = "<p class='metric-context'>No SHORT forex opportunities identified today.</p>"

    vix_level = "LOW"
    try:
        vix_val = float(macro.get('vix') or 0)
        vix_level = "HIGH" if vix_val > 20 else "MODERATE" if vix_val > 15 else "LOW"
    except:
        pass

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Forex Market Report - {today_str}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Outfit:wght@500;700&display=swap" rel="stylesheet">
    <style>
        {CSS_STYLES}
    </style>
</head>
<body>

<div class="container">
    <nav style="margin-bottom: 2rem; padding: 1rem 0; border-bottom: 1px solid var(--glass-border); display:flex; justify-content:space-between;">
        <a href="../../index.html" style="color: var(--accent-color); text-decoration: none; font-weight: 600;">&#8592; Back to Hub</a>
        <a href="../../analytics.html" style="color: var(--success); text-decoration: none; font-weight: 600;">📊 View Analytics & Win Rate</a>
    </nav>

    <header>
        <h1>Forex Market Intelligence Report</h1>
        <p style="text-align: center; color: var(--text-secondary); margin-top: -1.5rem; margin-bottom: 1rem;">{today_str}</p>
        <div style="display:flex; justify-content:center; gap:1rem; margin-bottom:3rem;">
            <span style="background:#10b98122; color:#10b981; border:1px solid #10b98144; padding:6px 18px; border-radius:20px; font-weight:700; font-size:0.85rem;">&#9650; {len(long_signals)} LONG</span>
            <span style="background:#ef444422; color:#ef4444; border:1px solid #ef444444; padding:6px 18px; border-radius:20px; font-weight:700; font-size:0.85rem;">&#9660; {len(short_signals)} SHORT</span>
            <span style="background:rgba(255,255,255,0.05); color:var(--text-secondary); border:1px solid rgba(255,255,255,0.1); padding:6px 18px; border-radius:20px; font-size:0.85rem;">DXY {macro['dxy']} &bull; {vix_level} Volatility</span>
        </div>
    </header>

    <!-- SECTION 1: MACRO -->
    <section>
        <h2>1. FX Macro Drivers & Sentiment</h2>
        <div class="details-grid">
            <div class="card">
                <h3>VIX (Volatility)</h3>
                <span class="metric-value" style="color: {macro['vix_color']}">{macro['vix']}</span>
                <span class="metric-context">{macro['vix_change']} from yesterday</span>
            </div>
            <div class="card">
                <h3>10Y Treasury Yield (TNX)</h3>
                <span class="metric-value">{macro['tnx']}</span>
                <span class="metric-context">{macro['tnx_change']} Yield</span>
            </div>
            <div class="card">
                <h3>DXY (US Dollar)</h3>
                <span class="metric-value">{macro['dxy']}</span>
                <span class="metric-context">{macro['dxy_change']} USD Strength</span>
            </div>
        </div>
    </section>

    <!-- SECTION 2: LONG SIGNALS -->
    <section>
        <h2 style="color: #10b981;">&#9650; 2. LONG Signals &mdash; Buy / Bullish Setups</h2>
        <p style="color: var(--text-secondary);">Pairs in oversold territory or with confirmed bullish momentum.</p>
        <div class="plan-grid">
            {long_cards_html}
        </div>
    </section>

    <!-- SECTION 3: SHORT SIGNALS -->
    <section>
        <h2 style="color: #ef4444;">&#9660; 3. SHORT Signals &mdash; Sell / Bearish Setups</h2>
        <p style="color: var(--text-secondary);">Pairs in overbought territory with potential for mean reversion.</p>
        <div class="plan-grid">
            {short_cards_html}
        </div>
    </section>

    <!-- SECTION 4: RISK MANAGEMENT -->
    {generate_risk_section()}

    <!-- SECTION 5: SIGNALS AUDIT -->
    <section>
        <h2>5. Audit & Tracking</h2>
        <div class="card">
            <p>Signals generated algorithmically and tracked in real-time.</p>
            <p><small style="color: var(--text-secondary)">Total Signals Today: {len(signals)} ({len(long_signals)} LONG / {len(short_signals)} SHORT)</small></p>
        </div>
    </section>

    <div class="footer">
        <p>Generated by Antigravity Autonomous Forex System &bull; {today_str}</p>
    </div>
</div>

</body>
</html>
"""
    return html

def generate_markdown_report(signals, macro):
    today_str = datetime.datetime.now().strftime("%B %d, %Y")
    
    # Categorize Signals (Forex Contexts)
    value_signals = [s for s in signals if any(kw in s.get("context", "") for kw in ["OVERSOLD", "REJECTION", "BOUNCE"])]
    momentum_signals = [s for s in signals if any(kw in s.get("context", "") for kw in ["MOMENTUM", "TREND", "CONTINUATION"])]
    
    md = f"""# Informe Mercado Divisas
{today_str}

## 1. Contexto Macro & Sentiment
El Índice Dólar (DXY) en {macro['dxy']} marca la pauta. Un DXY fuerte presiona a pares como EURUSD y GBPUSD a la baja.

**VIX (Volatilidad)**
{macro['vix']}
{macro['vix_change']} respecto ayer

**Bonos 10Y (TNX)**
{macro['tnx']}
{macro['tnx_change']} Yield

**DXY (Dólar)**
{macro['dxy']}
{macro['dxy_change']} Fuerza USD

## 2. Value Plays: Reversiones y Soportes
Selección de pares en zonas de agotamiento (RSI) con potencial de giro.

"""
    if not value_signals:
        md += "No se encontraron oportunidades de valor hoy.\n\n"
    for s in value_signals:
        md += f"### {s['ticker']}\n"
        md += f"- Entrada: {s['entry_price']:.5f}\n"
        md += f"- Target: {s['target_price']:.5f}\n"
        md += f"- Stop: {s['stop_loss']:.5f}\n"
        md += f"- Nota: {s['notes']}\n\n"

    md += "## 3. Momentum & Seguimiento de Tendencia\n"
    md += "Pares con fuerza relativa y confirmación de tendencia.\n\n"
    if not momentum_signals:
        md += "No se encontraron oportunidades de momentum/breakout hoy.\n\n"
    for s in momentum_signals:
        md += f"### {s['ticker']}\n"
        md += f"- Entrada: {s['entry_price']:.5f}\n"
        md += f"- Target: {s['target_price']:.5f}\n"
        md += f"- Stop: {s['stop_loss']:.5f}\n"
        md += f"- Nota: {s['notes']}\n\n"

    md += f"""## 4. Gestión de Riesgo Forex
- **Apalancamiento:** El Forex permite alto apalancamiento. Úsalo con precaución extrema.
- **Noticias Macro:** Evita operar durante NFP, FOMC o IPC si no gestionas bien la volatilidad.
- **DXY Correlation:** Vigila siempre el Índice Dólar; es el motor de los pares mayores.
- **Stop Loss:** Obligatorio. La liquidez puede desaparecer en eventos imprevistos.

## 5. Auditoría
Señales generadas algorítmicamente y auditadas en tiempo real.

Total Señales Hoy: {len(signals)}

---
Generado por Antigravity Forex System
"""
    return md

def run_generator(signals_file, output_dir):
    print("⚙️ Generando reportes Divisas desde datos...")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(signals_file, 'r', encoding='utf-8') as f:
        all_signals = json.load(f)
        
    today_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Filter to only display PENDING or ACTIVE signals
    open_signals = [
        s for s in all_signals 
        if s.get("status") in ["PENDING", "ACTIVE"]
    ]
    
    # De-duplicate: Keep only the most recent signal for each ticker
    unique_signals = {}
    for s in open_signals:
        ticker = s.get("ticker")
        unique_signals[ticker] = s
        
    signals = list(unique_signals.values())
        
    macro = fetch_macro_data()
    
    today = datetime.datetime.now().strftime("%Y_%m_%d")
    base_name = f"forex_market_report_{today}"
    
    # HTML (Rich)
    html_content = generate_html_report(signals, macro)
    html_path = os.path.join(output_dir, f"{base_name}.html")
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"✅ HTML generado: {html_path}")
    
    # MD (Detailed)
    md_content = generate_markdown_report(signals, macro)
    md_path = os.path.join(output_dir, f"{base_name}.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print(f"✅ Markdown generado: {md_path}")

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    SIGNALS_FILE = os.path.join(BASE_DIR, 'data', 'signals.json')
    REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
    
    run_generator(SIGNALS_FILE, REPORTS_DIR)
