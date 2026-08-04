import os
import json
import datetime
import sys

# Configure stdout/stderr encoding for Windows console compatibility
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MARKET_FILES = {
    "Stocks": os.path.join(BASE_DIR, "data", "signals.json"),
    "Crypto": os.path.join(BASE_DIR, "infocryptos", "data", "signals.json"),
    "Forex": os.path.join(BASE_DIR, "infofx", "data", "signals.json")
}

ANALYTICS_JSON = os.path.join(BASE_DIR, "data", "analytics.json")

MAX_RR = 5.0

def calculate_rr(entry, stop, target, direction="LONG"):
    """Reward/risk of a signal, or None if it is not measurable.

    Returning None (rather than a placeholder) keeps malformed signals out of
    the P&L instead of crediting them with an invented ratio.
    """
    try:
        entry = float(entry)
        stop = float(stop)
        target = float(target)
    except (TypeError, ValueError):
        return None

    risk = abs(entry - stop)
    reward = abs(target - entry)
    # A stop within 0.1% of entry is rounding noise, not a real risk level.
    if risk <= abs(entry) * 0.001 or risk == 0:
        return None
    return min(round(reward / risk, 2), MAX_RR)

def generate_analytics_data():
    print("📊 Generating Analytics & Performance Data...")
    
    all_signals = []
    market_stats = {
        "Stocks": {"total": 0, "wins": 0, "losses": 0, "pending": 0, "active": 0, "expired": 0, "win_rate": 0.0, "total_r": 0.0},
        "Crypto": {"total": 0, "wins": 0, "losses": 0, "pending": 0, "active": 0, "expired": 0, "win_rate": 0.0, "total_r": 0.0},
        "Forex":  {"total": 0, "wins": 0, "losses": 0, "pending": 0, "active": 0, "expired": 0, "win_rate": 0.0, "total_r": 0.0}
    }
    
    total_wins = 0
    total_losses = 0
    total_r = 0.0
    gross_profit_r = 0.0   # sum of R won, for the real profit factor
    gross_loss_r = 0.0     # sum of R lost (positive number)
    invalid_signals = 0

    closed_trades = []     # (date, market, ticker, r) built into the equity curve

    for market_name, file_path in MARKET_FILES.items():
        if not os.path.exists(file_path):
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                signals = json.load(f)
            except json.JSONDecodeError:
                signals = []
                
        for s in signals:
            s['market'] = market_name
            status = s.get("status", "PENDING")
            rr = calculate_rr(s.get("entry_price"), s.get("stop_loss"), s.get("target_price"), s.get("type", "LONG"))
            s['rr_ratio'] = rr
            
            market_stats[market_name]["total"] += 1

            is_closed = status in ["HIT_TARGET", "CLOSED_WIN", "HIT_STOP", "CLOSED_LOSS"]
            if is_closed and rr is None:
                # Cannot score a trade whose risk is undefined; count it, but
                # keep it out of the win rate and the R totals.
                invalid_signals += 1
                all_signals.append(s)
                continue

            if status in ["HIT_TARGET", "CLOSED_WIN"]:
                market_stats[market_name]["wins"] += 1
                market_stats[market_name]["total_r"] += rr
                total_wins += 1
                total_r += rr
                gross_profit_r += rr
                closed_trades.append((s.get("date", ""), market_name, s.get("ticker"), rr))
            elif status in ["HIT_STOP", "CLOSED_LOSS"]:
                market_stats[market_name]["losses"] += 1
                market_stats[market_name]["total_r"] -= 1.0
                total_losses += 1
                total_r -= 1.0
                gross_loss_r += 1.0
                closed_trades.append((s.get("date", ""), market_name, s.get("ticker"), -1.0))
            elif status == "ACTIVE":
                market_stats[market_name]["active"] += 1
            elif status == "EXPIRED":
                # Never filled within the entry window; not a trade either way.
                market_stats[market_name]["expired"] += 1
            else:
                market_stats[market_name]["pending"] += 1

            all_signals.append(s)

    # Equity curve in chronological order, one point per closed trade. Open
    # signals contribute nothing until they resolve.
    equity_curve = []
    cumulative_r = 0.0
    for date, market_name, ticker, r in sorted(closed_trades, key=lambda x: x[0]):
        cumulative_r += r
        equity_curve.append({
            "date": date,
            "ticker": ticker,
            "market": market_name,
            "cumulative_r": round(cumulative_r, 2)
        })

    # Win rates. With no closed trades the honest value is zero, not a guess.
    for m in market_stats:
        closed = market_stats[m]["wins"] + market_stats[m]["losses"]
        market_stats[m]["win_rate"] = round((market_stats[m]["wins"] / closed) * 100, 1) if closed else 0.0
        market_stats[m]["total_r"] = round(market_stats[m]["total_r"], 2)

    # Two entry modes run side by side: the original engine and the pullback
    # variant that enters at the baseline stop. They are different strategies,
    # so the point of the dashboard is to keep their records apart.
    by_mode = {}
    for mode in ("baseline", "stop_hold"):
        sub = [s for s in all_signals if s.get("mode", "baseline") == mode]
        w = l = 0
        gp = gl = 0.0
        for s in sub:
            rr = s.get("rr_ratio")
            if s.get("status") in ("HIT_TARGET", "CLOSED_WIN") and rr:
                w += 1
                gp += rr
            elif s.get("status") in ("HIT_STOP", "CLOSED_LOSS") and rr:
                l += 1
                gl += 1.0
        closed_n = w + l
        filled = sum(1 for s in sub
                     if s.get("status") not in ("PENDING", "EXPIRED"))
        by_mode[mode] = {
            "signals": len(sub),
            "closed": closed_n,
            "wins": w,
            "losses": l,
            "win_rate": round(100.0 * w / closed_n, 1) if closed_n else 0.0,
            "total_r": round(gp - gl, 2),
            "expectancy_r": round((gp - gl) / closed_n, 3) if closed_n else 0.0,
            "profit_factor": round(gp / gl, 2) if gl else 0.0,
            "expired": sum(1 for s in sub if s.get("status") == "EXPIRED"),
            "fill_rate": round(100.0 * filled / len(sub), 1) if sub else 0.0,
        }

    total_closed = total_wins + total_losses
    global_win_rate = round((total_wins / total_closed) * 100, 1) if total_closed > 0 else 0.0
    # Real profit factor: R won divided by R lost.
    profit_factor = round(gross_profit_r / gross_loss_r, 2) if gross_loss_r > 0 else 0.0
    expectancy = round(total_r / total_closed, 3) if total_closed > 0 else 0.0

    analytics_summary = {
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "global": {
            "total_signals": len(all_signals),
            "closed_trades": total_closed,
            "wins": total_wins,
            "losses": total_losses,
            "win_rate": global_win_rate,
            "total_r": round(total_r, 2),
            "profit_factor": profit_factor,
            "gross_profit_r": round(gross_profit_r, 2),
            "gross_loss_r": round(gross_loss_r, 2),
            "expectancy_r": expectancy,
            "invalid_signals": invalid_signals
        },
        "by_market": market_stats,
        "by_mode": by_mode,
        "equity_curve": equity_curve,
        "recent_signals": sorted(all_signals, key=lambda x: x.get("date", ""), reverse=True)[:30]
    }

    with open(ANALYTICS_JSON, 'w', encoding='utf-8') as f:
        json.dump(analytics_summary, f, indent=4, ensure_ascii=False)

    # Inject directly into analytics.html for local file:// compatibility without CORS issues
    analytics_html_path = os.path.join(BASE_DIR, "analytics.html")
    if os.path.exists(analytics_html_path):
        try:
            with open(analytics_html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            import re
            json_str = json.dumps(analytics_summary, ensure_ascii=False)
            pattern = r'window\.ANALYTICS_DATA\s*=\s*.*?;'
            replacement = f'window.ANALYTICS_DATA = {json_str};'
            updated_html, count = re.subn(pattern, replacement, html_content, flags=re.DOTALL)
            if count > 0:
                with open(analytics_html_path, 'w', encoding='utf-8') as f:
                    f.write(updated_html)
                print("💉 Injected dynamic analytics dataset into analytics.html successfully.")
        except Exception as ie:
            print(f"⚠️ Error injecting into analytics.html: {ie}")

    print(f"✅ Analytics data saved to {ANALYTICS_JSON}")
    return analytics_summary

if __name__ == "__main__":
    generate_analytics_data()
