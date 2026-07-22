import json
import datetime
import os
import random

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

try:
    from scripts.fetch_sentiment import fetch_crypto_fear_and_greed, get_stock_sentiment
    from scripts.fetch_calendar import fetch_economic_calendar
except ImportError:
    try:
        from fetch_sentiment import fetch_crypto_fear_and_greed, get_stock_sentiment
        from fetch_calendar import fetch_economic_calendar
    except ImportError:
        def fetch_crypto_fear_and_greed(): return {"value": 50, "classification": "Neutral", "color": "#f59e0b"}
        def get_stock_sentiment(v): return {"value": 50, "classification": "Neutral", "color": "#f59e0b"}
        def fetch_economic_calendar(): return {"high_impact_risk": False, "events": []}

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

    # Context badge (secondary)
    context_label = context.replace("_", " ").title() if context else "Signal"

    # Safe DOM ID for ticker
    chart_id = f"tv_chart_{ticker.replace('=', '_').replace('-', '_').replace('^', '_')}"
    
    raw_entry = price
    raw_stop = signal.get('stop_loss', 0)
    raw_target = signal.get('target_price', 0)

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
                
                <!-- TradingView Lightweight Chart Container -->
                <div id="{chart_id}" style="width: 100%; height: 160px; margin: 1rem 0; border-radius: 8px; overflow: hidden; background: #0f172a; border: 1px solid rgba(255,255,255,0.05);"></div>

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
                        <span class="level-label">Target</span>
                        <span class="level-value">{target}</span>
                    </div>
                </div>
                <div style="margin-top: 1rem; text-align: right;">
                    <span class="risk-reward" style="background: {rr_color}20; color: {rr_color}; border: 1px solid {rr_color}40;">R:R {rr_text}</span>
                </div>
            </div>
            <script>
            document.addEventListener("DOMContentLoaded", function() {{
                const el = document.getElementById("{chart_id}");
                if (el && typeof LightweightCharts !== 'undefined') {{
                    const chart = LightweightCharts.createChart(el, {{
                        layout: {{ backgroundColor: '#0f172a', textColor: '#94a3b8' }},
                        grid: {{ vertLines: {{ color: 'rgba(255, 255, 255, 0.03)' }}, horzLines: {{ color: 'rgba(255, 255, 255, 0.03)' }} }},
                        timeScale: {{ visible: false }},
                        rightPriceScale: {{ borderVisible: false }}
                    }});
                    const line = chart.addLineSeries({{ color: '{'#10b981' if direction == 'LONG' else '#ef4444'}', lineWidth: 2 }});
                    line.createPriceLine({{ price: {raw_entry}, color: '#3b82f6', lineWidth: 2, lineStyle: LightweightCharts.LineStyle.Solid, title: 'ENTRADA' }});
                    line.createPriceLine({{ price: {raw_target}, color: '#10b981', lineWidth: 2, lineStyle: LightweightCharts.LineStyle.Dashed, title: 'TARGET (TP)' }});
                    line.createPriceLine({{ price: {raw_stop}, color: '#ef4444', lineWidth: 2, lineStyle: LightweightCharts.LineStyle.Dashed, title: 'STOP (SL)' }});
                }}
            }});
            </script>
    """
    return html

def generate_risk_section():
    weekday = datetime.datetime.now().strftime("%A")
    warning = ""
    if weekday == "Friday":
        warning = "<li><strong>Friday Risk Warning:</strong> Liquidity drops significantly after 2:00 PM ET. Close intraday positions prior to weekend close.</li>"
    
    html = f"""
    <section>
        <h2>4. Risk & Capital Management</h2>
        <div class="card" style="border-left: 4px solid var(--accent-color);">
            <ul>
                <li><strong>Position Sizing:</strong> Maintain risk per trade at 1-2% of total account capital.</li>
                <li><strong>Total Exposure:</strong> Maximum 3 simultaneous positions to avoid correlated drawdown.</li>
                {warning}
            </ul>
        </div>
    </section>
    """
    return html

def generate_html_report(signals, macro):
    today_str = datetime.datetime.now().strftime("%B %d, %Y")

    # Split by direction
    long_signals = [s for s in signals if s.get("type", "LONG").upper() == "LONG"]
    short_signals = [s for s in signals if s.get("type", "SHORT").upper() == "SHORT"]

    # Fetch Sentiment & Calendar
    stock_sent = get_stock_sentiment(macro.get('vix', 15))
    eco_cal = fetch_economic_calendar()

    # Generate Cards HTML
    long_cards_html = "".join([generate_signal_card(s, False) for s in long_signals])
    short_cards_html = "".join([generate_signal_card(s, False) for s in short_signals])

    if not long_cards_html:
        long_cards_html = "<p class='metric-context'>No LONG opportunities identified today.</p>"
    if not short_cards_html:
        short_cards_html = "<p class='metric-context'>No SHORT opportunities identified today.</p>"

    vix_level = "LOW"
    try:
        vix_val = float(macro.get('vix') or 0)
        vix_level = "HIGH" if vix_val > 20 else "MODERATE" if vix_val > 15 else "LOW"
    except:
        pass

    # Calendar Events HTML
    cal_html = ""
    for ev in eco_cal.get("events", []):
        risk_color = "var(--danger)" if ev.get("impact") in ["HIGH", "ALTO"] else "var(--accent-color)"
        cal_html += f"""
        <div style="display:flex; justify-content:space-between; align-items:center; padding:0.5rem 0; border-bottom:1px solid rgba(255,255,255,0.05);">
            <div>
                <strong style="color:white;">{ev['event']}</strong>
                <div style="font-size:0.8rem; color:var(--text-secondary);">{ev['time']} &bull; {ev['currency']}</div>
            </div>
            <span style="background:{risk_color}22; color:{risk_color}; border:1px solid {risk_color}44; padding:2px 8px; border-radius:4px; font-size:0.75rem; font-weight:bold;">{ev['impact']} IMPACT</span>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Market Report - {today_str}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Outfit:wght@500;700&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        {CSS_STYLES}
    </style>
</head>
<body>

<div class="container">
    <nav style="margin-bottom: 2rem; padding: 1rem 0; border-bottom: 1px solid var(--glass-border); display:flex; justify-content:space-between;">
        <a href="../index.html" style="color: var(--accent-color); text-decoration: none; font-weight: 600;">&#8592; Back to Hub</a>
        <a href="../analytics.html" style="color: var(--success); text-decoration: none; font-weight: 600;">📊 View Analytics & Win Rate</a>
    </nav>

    <header>
        <h1>Daily Market Intelligence Report</h1>
        <p style="text-align: center; color: var(--text-secondary); margin-top: -1.5rem; margin-bottom: 1rem;">{today_str}</p>
        <div style="display:flex; justify-content:center; gap:1rem; margin-bottom:3rem; flex-wrap:wrap;">
            <span style="background:#10b98122; color:#10b981; border:1px solid #10b98144; padding:6px 18px; border-radius:20px; font-weight:700; font-size:0.85rem;">&#9650; {len(long_signals)} LONG</span>
            <span style="background:#ef444422; color:#ef4444; border:1px solid #ef444444; padding:6px 18px; border-radius:20px; font-weight:700; font-size:0.85rem;">&#9660; {len(short_signals)} SHORT</span>
            <span style="background:rgba(255,255,255,0.05); color:var(--text-secondary); border:1px solid rgba(255,255,255,0.1); padding:6px 18px; border-radius:20px; font-size:0.85rem;">VIX {macro['vix']} &bull; {vix_level}</span>
            <span style="background:{stock_sent['color']}22; color:{stock_sent['color']}; border:1px solid {stock_sent['color']}44; padding:6px 18px; border-radius:20px; font-weight:700; font-size:0.85rem;">Sentiment: {stock_sent['classification']} ({stock_sent['value']}/100)</span>
        </div>
    </header>

    <!-- SECTION 1: MACRO & SENTIMENT -->
    <section>
        <h2>1. Macroeconomic Context & Market Sentiment</h2>
        <div class="details-grid">
            <div class="card">
                <h3>VIX Index (Volatility)</h3>
                <span class="metric-value" style="color: {macro['vix_color']}">{macro['vix']}</span>
                <span class="metric-context">{macro['vix_change']} vs yesterday</span>
            </div>
            <div class="card">
                <h3>10Y Treasury Yield (TNX)</h3>
                <span class="metric-value">{macro['tnx']}</span>
                <span class="metric-context">{macro['tnx_change']} Yield</span>
            </div>
            <div class="card">
                <h3>US Dollar Index (DXY)</h3>
                <span class="metric-value">{macro['dxy']}</span>
                <span class="metric-context">{macro['dxy_change']} USD Strength</span>
            </div>
        </div>

        <!-- ECONOMIC CALENDAR CARD -->
        <div class="card" style="margin-top:1.5rem; border-left: 4px solid {'var(--danger)' if eco_cal['high_impact_risk'] else 'var(--accent-color)'};">
            <h3>📅 Key Economic Calendar Events Today</h3>
            {cal_html}
        </div>
    </section>

    <!-- SECTION 2: LONG SIGNALS -->
    <section>
        <h2 style="color: #10b981;">&#9650; 2. LONG Signals &mdash; Buy / Bullish Setups</h2>
        <p style="color: var(--text-secondary);">Assets displaying bullish technical setups: oversold bounce, breakout or trend continuation.</p>
        <div class="plan-grid">
            {long_cards_html}
        </div>
    </section>

    <!-- SECTION 3: SHORT SIGNALS -->
    <section>
        <h2 style="color: #ef4444;">&#9660; 3. SHORT Signals &mdash; Sell / Bearish Setups</h2>
        <p style="color: var(--text-secondary);">Assets in extreme overbought territory or breaking down below key moving averages.</p>
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
            <p>Signals algorithmically generated and tracked in real-time. Target prices are calculated using ATR and technical pivot levels.</p>
            <p><small style="color: var(--text-secondary)">Total Signals Today: {len(signals)} ({len(long_signals)} LONG / {len(short_signals)} SHORT)</small></p>
        </div>
    </section>

    <div class="footer">
        <p>Generated by Antigravity Autonomous Trading System &bull; {today_str}</p>
    </div>
</div>

</body>
</html>
"""
    return html

def run_generator(signals_file, output_dir):
    print("⚙️ Generando reportes desde datos...")
    
    with open(signals_file, 'r', encoding='utf-8') as f:
        all_signals = json.load(f)
        
    today_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Filter to only display PENDING or ACTIVE signals (no historical closed signals)
    open_signals = [
        s for s in all_signals 
        if s.get("status") in ["PENDING", "ACTIVE"]
    ]
    
    # De-duplicate: Keep only the most recent signal for each ticker
    unique_signals = {}
    for s in open_signals:
        ticker = s.get("ticker")
        # Since signals are appended, newer signals are later in the list. Overwrite to keep latest.
        unique_signals[ticker] = s
        
    signals = list(unique_signals.values())
        
    macro = fetch_macro_data()
    
    today = datetime.datetime.now().strftime("%Y_%m_%d")
    base_name = f"daily_market_report_{today}"
    
    # HTML (Rich)
    html_content = generate_html_report(signals, macro)
    html_path = os.path.join(output_dir, f"{base_name}.html")
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"✅ HTML generado: {html_path}")
    
    # MD (Simple - for reference or basic view)
    md_path = os.path.join(output_dir, f"{base_name}.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# Informe Diario\n\nVer archivo HTML para el informe completo y estructurado.")
    print(f"✅ Markdown generado: {md_path}")

if __name__ == "__main__":
    run_generator("d:/Docker/infoacc/data/signals.json", "d:/Docker/infoacc/reports")
