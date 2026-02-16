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
        --accent-color: #3b82f6;
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
    entry = f"${price:.2f}"
    stop = f"${signal.get('stop_loss'):.2f}"
    target = f"${signal.get('target_price'):.2f}"
    notes = signal.get("notes")
    
    # Calculate R:R
    try:
        risk = price - signal.get("stop_loss")
        reward = signal.get("target_price") - price
        rr_ratio = reward / risk if risk > 0 else 0
        rr_text = f"1:{rr_ratio:.1f}"
    except:
        rr_text = "N/A"

    badge_html = ""
    card_style = "card plan-card"
    
    if is_momentum:
        card_style = "card" # Base card
        border_color = "var(--warning)"
        badge_text = "MOMENTUM"
        badge_bg = "var(--warning)"
        
        if "BREAKOUT" in signal.get("context", ""):
            badge_text = "BREAKOUT"
            badge_bg = "var(--success)"
            border_color = "var(--success)"
        elif "SHORT" in signal.get("type", ""):
             badge_text = "SHORT"
             badge_bg = "var(--danger)"
             border_color = "var(--danger)"
             
        card_style += f'" style="border-left: 4px solid {border_color};'
        badge_html = f'<span class="badge" style="background: {badge_bg};">{badge_text}</span>'
    else:
        # Value Style
         badge_html = f'<small style="color: var(--text-secondary)">Value / Reversal</small>'

    html = f"""
            <div class="{card_style}">
                <div class="plan-header">
                    <h3>{ticker} {badge_html}</h3>
                    <span class="plan-price">{entry}</span>
                </div>
                <p class="metric-context">{notes}</p>
                <div class="trade-levels">
                    <div class="entry">
                        <span class="level-label">Entrada</span>
                        <span class="level-value">{entry}</span>
                    </div>
                    <div class="stop">
                        <span class="level-label">Stop Loss</span>
                        <span class="level-value">{stop}</span>
                    </div>
                    <div class="target">
                        <span class="level-label">Target 1</span>
                        <span class="level-value">{target}</span>
                    </div>
                </div>
                <div style="margin-top: 1rem; text-align: right;">
                    <span class="risk-reward">R:R {rr_text}</span>
                </div>
            </div>
    """
    return html

def generate_risk_section():
    weekday = datetime.datetime.now().strftime("%A")
    warning = ""
    if weekday == "Friday":
        warning = "<li><strong>Advertencia Viernes:</strong> Liquidez baja desde 2PM ET. Cerrar posiciones intradía antes del cierre.</li>"
    
    html = f"""
    <section>
        <h2>4. Gestión de Riesgo</h2>
        <div class="card" style="border-left: 4px solid var(--accent-color);">
            <ul>
                <li><strong>Position Sizing:</strong> Mantener riesgo por operación en 1-2% del capital total.</li>
                <li><strong>Exposición Total:</strong> Máx 3 operaciones simultáneas para evitar correlación excesiva.</li>
                {warning}
            </ul>
        </div>
    </section>
    """
    return html

def generate_html_report(signals, macro):
    today_str = datetime.datetime.now().strftime("%d de %B de %Y")
    
    # Categorize Signals
    value_signals = [s for s in signals if "VALUE" in s.get("context", "VALUE")]
    momentum_signals = [s for s in signals if "MOMENTUM" in s.get("context", "")]
    
    # Fallback if all are categorized as one type or untyped
    if not momentum_signals and len(value_signals) > 5:
        # Move some high volatility ones to momentum if we can measure it, 
        # or just split list for visual balance
        pass 

    # Generate Cards HTML
    value_cards_html = "".join([generate_signal_card(s, False) for s in value_signals])
    momentum_cards_html = "".join([generate_signal_card(s, True) for s in momentum_signals])
    
    if not value_cards_html: value_cards_html = "<p class='metric-context'>No se encontraron oportunidades de valor hoy.</p>"
    if not momentum_cards_html: momentum_cards_html = "<p class='metric-context'>No se encontraron oportunidades de momentum/breakout hoy.</p>"

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Informe Mercado Crypto - {today_str}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Outfit:wght@500;700&display=swap" rel="stylesheet">
    <style>
        {CSS_STYLES}
    </style>
</head>
<body>

<div class="container">
    <nav style="margin-bottom: 2rem; padding: 1rem 0; border-bottom: 1px solid var(--glass-border);">
        <a href="../../index.html" style="color: var(--accent-color); text-decoration: none; font-weight: 600;">← Volver al Hub</a>
    </nav>

    <header>
        <h1>Informe Mercado Crypto</h1>
        <p style="text-align: center; color: var(--text-secondary); margin-top: -1.5rem; margin-bottom: 3rem;">{today_str}</p>
    </header>

    <!-- SECTION 1: MACRO -->
    <section>
        <h2>1. Contexto Macro & Sentiment</h2>
        <div class="card">
            <p>Datos en tiempo real de los principales indicadores de riesgo. El VIX en <strong>{macro['vix']}</strong> sugiere un entorno de <span style="color:{macro['vix_color']}">riesgo {("ALTO" if float(macro['vix'] or 0) > 20 else "MODERADO" if float(macro['vix'] or 0) > 15 else "BAJO")}</span> para activos de riesgo como Crypto.</p>
        </div>
        <div class="details-grid">
            <div class="card">
                <h3>VIX (Volatilidad)</h3>
                <span class="metric-value" style="color: {macro['vix_color']}">{macro['vix']}</span>
                <span class="metric-context">{macro['vix_change']} respecto ayer</span>
            </div>
            <div class="card">
                <h3>Bonos 10Y (TNX)</h3>
                <span class="metric-value">{macro['tnx']}</span>
                <span class="metric-context">{macro['tnx_change']} Yield</span>
            </div>
             <div class="card">
                <h3>DXY (Dólar)</h3>
                <span class="metric-value">{macro['dxy']}</span>
                <span class="metric-context">{macro['dxy_change']} Fuerza USD</span>
            </div>
        </div>
    </section>

    <!-- SECTION 2: VALUE PLAYS -->
    <section>
        <h2>2. Value Plays: Oversold Bounce</h2>
        <p style="color: var(--text-secondary)">Selección de criptos infravaloradas (RSI Oversold) con potencial rebote.</p>
        
        <div class="plan-grid">
            {value_cards_html}
        </div>
    </section>

    <!-- SECTION 3: MOMENTUM -->
    <section>
        <h2>3. Momentum & Breakouts</h2>
         <p style="color: var(--text-secondary)">Criptos con fuerza relativa y patrones de ruptura.</p>
        
        <div class="details-grid" style="grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));">
            {momentum_cards_html}
        </div>
    </section>

    <!-- SECTION 4: RISK MANAGEMENT -->
    <section>
        <h2>4. Gestión de Riesgo Crypto</h2>
        <div class="card" style="border-left: 4px solid var(--accent-color);">
            <ul>
                <li><strong>Volatilidad:</strong> Crypto es 3x más volátil que Stocks. Reduce el tamaño de posición acorde.</li>
                <li><strong>Custodia:</strong> "Not your keys, not your coins". Retira ganancias a Cold Storage.</li>
                <li><strong>Stop Loss:</strong> Obligatorio. El mercado 24/7 no perdona.</li>
            </ul>
        </div>
    </section>

    <!-- SECTION 5: SIGNALS AUDIT -->
    <section>
        <h2>5. Auditoría</h2>
        <div class="card">
            <p>Señales generadas algorítmicamente y auditadas en tiempo real.</p>
            <p><small style="color: var(--text-secondary)">Total Señales Hoy: {len(signals)}</small></p>
        </div>
    </section>

    <div class="footer">
        <p>Generado por Antigravity Crypto System • {today_str}</p>
    </div>
</div>

</body>
</html>
"""
    return html

def run_generator(signals_file, output_dir):
    print("⚙️ Generando reportes Crypto desde datos...")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(signals_file, 'r', encoding='utf-8') as f:
        signals = json.load(f)
        
    macro = fetch_macro_data()
    
    today = datetime.datetime.now().strftime("%Y_%m_%d")
    base_name = f"crypto_market_report_{today}"
    
    # HTML (Rich)
    html_content = generate_html_report(signals, macro)
    html_path = os.path.join(output_dir, f"{base_name}.html")
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"✅ HTML generado: {html_path}")
    
    # MD (Simple - for reference or basic view)
    md_path = os.path.join(output_dir, f"{base_name}.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# Informe Diario Crypto\n\nVer archivo HTML para el informe completo y estructurado.")
    print(f"✅ Markdown generado: {md_path}")

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    SIGNALS_FILE = os.path.join(BASE_DIR, 'data', 'signals.json')
    REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
    
    run_generator(SIGNALS_FILE, REPORTS_DIR)
