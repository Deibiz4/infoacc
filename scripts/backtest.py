"""Walk-forward backtest of the live signal engine.

The published metrics cover a handful of trades, which says nothing about
whether the strategies work. This replays the engine over years of history to
get a sample worth reading.

Fidelity rules, so the result describes production and not a lookalike:

  * Signals come from each market's own generate_signal(), imported from the
    scanner that runs in production. No reimplementation of the entry rules.
  * Indicators are rolling and therefore causal, so they are computed once per
    ticker and sliced; the value on day i never depends on day i+1.
  * Each day only sees data up to that day's close.
  * Dedup and the concentration caps are applied exactly as the scanners do,
    against the book as it stood on that day.
  * Signals resolve under track_signals.resolve_signal's rules: only sessions
    strictly after the signal date, fill when price trades through the entry,
    and the stop wins when a bar spans both levels.

Usage:
    python scripts/backtest.py --years 6
    python scripts/backtest.py --years 6 --market Stocks --by-year
"""
import argparse
import contextlib
import importlib.util
import io
import json
import os
import sys
import warnings
from collections import defaultdict

warnings.filterwarnings("ignore")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

import pandas as pd
import yfinance as yf

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_scanner(name, path):
    """Import a market's scanner under its own module name."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SCANNERS = {
    "Stocks": load_scanner(
        "scanner_stocks", os.path.join(SCRIPT_DIR, "market_scanner.py")
    ),
    "Crypto": load_scanner(
        "scanner_crypto",
        os.path.join(BASE_DIR, "infocryptos", "scripts", "market_scanner.py"),
    ),
    "Forex": load_scanner(
        "scanner_forex",
        os.path.join(BASE_DIR, "infofx", "scripts", "market_scanner.py"),
    ),
}


dropped_by_cap = defaultdict(int)


def signal_name(market, yf_ticker):
    """The ticker as the scanner would store it."""
    if market == "Crypto":
        return yf_ticker.replace("-USD", "")
    if market == "Forex":
        return SCANNERS["Forex"].clean_name(yf_ticker)
    return yf_ticker


def fetch(tickers, years):
    period = f"{years}y"
    print(f"Downloading {len(tickers)} tickers, {period} of daily bars...")
    raw = yf.download(
        tickers, period=period, group_by="ticker", progress=False, auto_adjust=True
    )
    frames = {}
    for t in tickers:
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                level = 0 if t in raw.columns.get_level_values(0) else 1
                df = raw.xs(t, level=level, axis=1)
            else:
                df = raw
            df = df.dropna(how="all")
        except Exception:
            continue
        if not df.empty and "Close" in df.columns:
            frames[t] = df
    print(f"  got usable history for {len(frames)}/{len(tickers)} tickers")
    return frames


def advance(sig, high, low):
    """Move one signal forward over a single bar. Mirrors resolve_signal."""
    status = sig["status"]
    if status == "PENDING" and low <= sig["entry_price"] <= high:
        status = "ACTIVE"
    if status == "ACTIVE":
        if sig["type"] == "LONG":
            if low <= sig["stop_loss"]:
                status = "HIT_STOP"
            elif high >= sig["target_price"]:
                status = "HIT_TARGET"
        else:
            if high >= sig["stop_loss"]:
                status = "HIT_STOP"
            elif low <= sig["target_price"]:
                status = "HIT_TARGET"
    return status


def rr_of(sig):
    risk = abs(sig["entry_price"] - sig["stop_loss"])
    if risk <= abs(sig["entry_price"]) * 0.001:
        return None
    return min(abs(sig["target_price"] - sig["entry_price"]) / risk, 5.0)


def run_market(market, years, warmup):
    scanner = SCANNERS[market]
    frames = fetch(list(scanner.TICKERS), years)
    if not frames:
        return []

    # Indicators once per ticker; rolling windows are causal so slicing later is
    # equivalent to recomputing on each day's truncated history.
    prepared = {}
    for t, df in frames.items():
        d = scanner.calculate_indicators(df.copy())
        if "SMA_50" in d.columns:
            prepared[t] = d

    calendar = sorted({d for df in prepared.values() for d in df.index})
    if len(calendar) <= warmup:
        print(f"  {market}: not enough history, skipping.")
        return []
    calendar = calendar[warmup:]

    positions = []   # open signals
    closed = []
    signalled_on = defaultdict(set)  # date -> tickers already signalled

    print(f"  {market}: simulating {len(calendar)} sessions "
          f"({calendar[0].date()} -> {calendar[-1].date()})")

    for day in calendar:
        # 1. Advance the open book on this bar, before anything new is added.
        still_open = []
        for sig in positions:
            df = prepared[sig["_yf"]]
            if day not in df.index or day <= sig["_created"]:
                still_open.append(sig)
                continue
            row = df.loc[day]
            high, low = float(row["High"]), float(row["Low"])
            if pd.isna(high) or pd.isna(low):
                still_open.append(sig)
                continue
            sig["status"] = advance(sig, high, low)
            if sig["status"] in ("HIT_STOP", "HIT_TARGET"):
                sig["_closed"] = day
                closed.append(sig)
            else:
                still_open.append(sig)
        positions = still_open

        # 2. Generate today's candidates, with the same blocking the scanner uses.
        blocked = {s["ticker"] for s in positions} | signalled_on[day]
        candidates = []
        for yf_ticker, df in prepared.items():
            name = signal_name(market, yf_ticker)
            if name in blocked:
                continue
            idx = df.index.get_indexer([day])[0]
            if idx < 1:
                continue
            window = df.iloc[: idx + 1]
            try:
                sig = scanner.generate_signal(yf_ticker, window)
            except Exception:
                continue
            if not sig:
                continue
            sig["date"] = day.strftime("%Y-%m-%d")
            sig["_created"] = day
            sig["_yf"] = yf_ticker
            sig["status"] = "PENDING"
            candidates.append(sig)

        if not candidates:
            continue

        # 3. Same concentration caps as production, against the live book.
        # The scanner narrates what it drops; useful in a daily run, noise over
        # thousands of simulated sessions.
        with contextlib.redirect_stdout(io.StringIO()):
            admitted = scanner.apply_risk_limits(
                candidates, [{"status": s["status"]} for s in positions]
            )
            dropped_by_cap[market] += len(candidates) - len(admitted)
        for sig in admitted:
            signalled_on[day].add(sig["ticker"])
            positions.append(sig)

    for sig in positions:
        sig["_closed"] = None
        closed.append(sig)

    for sig in closed:
        sig["market"] = market
    return closed


def score(signals):
    """Aggregate closed trades into the metrics the dashboard publishes."""
    wins = losses = 0
    gross_win = gross_loss = 0.0
    unresolved = invalid = 0
    for s in signals:
        if s["status"] not in ("HIT_STOP", "HIT_TARGET"):
            unresolved += 1
            continue
        rr = rr_of(s)
        if rr is None:
            invalid += 1
            continue
        if s["status"] == "HIT_TARGET":
            wins += 1
            gross_win += rr
        else:
            losses += 1
            gross_loss += 1.0
    n = wins + losses
    return {
        "trades": n,
        "wins": wins,
        "losses": losses,
        "win_rate": 100.0 * wins / n if n else 0.0,
        "total_r": gross_win - gross_loss,
        "expectancy": (gross_win - gross_loss) / n if n else 0.0,
        "profit_factor": gross_win / gross_loss if gross_loss else 0.0,
        "unresolved": unresolved,
        "invalid": invalid,
    }


def max_drawdown(signals):
    """Deepest peak-to-trough decline of the R curve, in R."""
    seq = sorted(
        (s for s in signals if s["status"] in ("HIT_STOP", "HIT_TARGET") and s.get("_closed")),
        key=lambda s: s["_closed"],
    )
    peak = equity = 0.0
    worst = 0.0
    for s in seq:
        rr = rr_of(s)
        if rr is None:
            continue
        equity += rr if s["status"] == "HIT_TARGET" else -1.0
        peak = max(peak, equity)
        worst = min(worst, equity - peak)
    return worst


def trade_returns(signals):
    """Per-trade R outcomes, for cost and significance analysis."""
    out = []
    for s in signals:
        if s["status"] not in ("HIT_STOP", "HIT_TARGET"):
            continue
        rr = rr_of(s)
        if rr is None:
            continue
        out.append(rr if s["status"] == "HIT_TARGET" else -1.0)
    return out


def bootstrap_ci(returns, iters=10000, seed=0):
    """95% CI for mean R per trade, by resampling trades with replacement."""
    if len(returns) < 2:
        return (0.0, 0.0)
    import numpy as np

    rng = np.random.default_rng(seed)
    arr = np.asarray(returns)
    means = rng.choice(arr, size=(iters, arr.size), replace=True).mean(axis=1)
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


def fmt(label, m, width=26):
    return (
        f"  {label:<{width}} {m['trades']:>5}  {m['win_rate']:>5.1f}%  "
        f"{m['total_r']:>+8.1f}  {m['expectancy']:>+7.3f}  {m['profit_factor']:>5.2f}"
    )


HEADER = "  {:<26} {:>5}  {:>6}  {:>8}  {:>7}  {:>5}".format(
    "", "TRADES", "WIN%", "TOTAL R", "EXP R", "PF"
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=6)
    ap.add_argument("--warmup", type=int, default=220,
                    help="Sessions reserved for indicator warm-up (200-SMA needs 200)")
    ap.add_argument("--market", choices=list(SCANNERS), help="Limit to one market")
    ap.add_argument("--by-year", action="store_true")
    ap.add_argument("--out", default=os.path.join(BASE_DIR, "data", "backtest.json"))
    args = ap.parse_args()

    markets = [args.market] if args.market else list(SCANNERS)

    print("=== WALK-FORWARD BACKTEST ===")
    print(f"History: {args.years}y   Warm-up: {args.warmup} sessions\n")

    all_signals = []
    for market in markets:
        all_signals.extend(run_market(market, args.years, args.warmup))

    resolved = [s for s in all_signals if s["status"] in ("HIT_STOP", "HIT_TARGET")]
    if not resolved:
        print("\nNo trades resolved. Nothing to report.")
        return

    overall = score(all_signals)

    print("\n" + "=" * 78)
    print("OVERALL")
    print("=" * 78)
    print(HEADER)
    print(fmt("ALL MARKETS", overall))
    print(f"\n  Max drawdown: {max_drawdown(all_signals):.1f} R")
    print(f"  Signals never resolved (still open at end): {overall['unresolved']}")
    total_dropped = sum(dropped_by_cap.values())
    if total_dropped:
        print(f"  Candidates refused by the concentration caps: {total_dropped}")
    if overall["invalid"]:
        print(f"  Signals with undefined risk, excluded: {overall['invalid']}")

    print("\n" + "=" * 78)
    print("BY MARKET")
    print("=" * 78)
    print(HEADER)
    for market in markets:
        sub = [s for s in all_signals if s["market"] == market]
        if sub:
            print(fmt(market, score(sub)))

    print("\n" + "=" * 78)
    print("BY STRATEGY  (this is the one that matters)")
    print("=" * 78)
    print(HEADER)
    groups = defaultdict(list)
    for s in all_signals:
        groups[(s["market"], s.get("context", "?"))].append(s)
    for key in sorted(groups, key=lambda k: score(groups[k])["total_r"]):
        m = score(groups[key])
        if m["trades"]:
            print(fmt(f"{key[0][:6]:<6} {key[1]}", m))

    print("\n" + "=" * 78)
    print("BY DIRECTION")
    print("=" * 78)
    print(HEADER)
    for d in ("LONG", "SHORT"):
        sub = [s for s in all_signals if s.get("type") == d]
        if sub:
            print(fmt(d, score(sub)))

    if args.by_year:
        print("\n" + "=" * 78)
        print("BY YEAR")
        print("=" * 78)
        print(HEADER)
        years = defaultdict(list)
        for s in resolved:
            if s.get("_closed") is not None:
                years[s["_closed"].year].append(s)
        for y in sorted(years):
            print(fmt(str(y), score(years[y])))

    # Everything above is gross. A real trade pays spread, slippage and
    # commission, and the engine risks 1R per trade, so a fixed cost per trade
    # in R is the honest way to see how much edge has to exist for this to work.
    print("\n" + "=" * 78)
    print("COST SENSITIVITY  (results above are gross, before any trading cost)")
    print("=" * 78)
    all_r = trade_returns(all_signals)
    n = len(all_r)
    gross = sum(all_r)
    print(f"  {'cost per trade':<20} {'net R':>10} {'per trade':>12}")
    for cost in (0.0, 0.02, 0.05, 0.10, 0.20):
        net = gross - cost * n
        print(f"  {cost:>6.2f} R{'':<12} {net:>+10.1f} {net / n:>+12.3f}")
    print(f"\n  Break-even cost: {gross / n:+.4f} R per trade")
    print(f"  ({n} trades; a cost above that number makes the system a loser)")

    print("\n" + "=" * 78)
    print("IS THE EDGE REAL?  95% confidence interval on mean R per trade")
    print("=" * 78)
    print(f"  {'':<26} {'TRADES':>6} {'MEAN R':>9} {'95% CI':>22}")
    ci_groups = [("ALL MARKETS", all_signals)]
    ci_groups += [(d, [s for s in all_signals if s.get("type") == d])
                  for d in ("LONG", "SHORT")]
    best = sorted(groups, key=lambda k: score(groups[k])["total_r"], reverse=True)[:3]
    ci_groups += [(f"{k[0][:6]} {k[1]}", groups[k]) for k in best]
    for label, sub in ci_groups:
        r = trade_returns(sub)
        if len(r) < 2:
            continue
        lo, hi = bootstrap_ci(r)
        verdict = "" if lo > 0 else ("  <- includes zero" if hi > 0 else "  <- negative")
        print(f"  {label:<26} {len(r):>6} {sum(r)/len(r):>+9.3f}"
              f"   [{lo:+.3f}, {hi:+.3f}]{verdict}")

    payload = {
        "generated": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "gross_total_r": round(gross, 2),
        "trades": n,
        "breakeven_cost_r": round(gross / n, 4) if n else 0.0,
        "years": args.years,
        "overall": overall,
        "max_drawdown_r": round(max_drawdown(all_signals), 2),
        "by_market": {m: score([s for s in all_signals if s["market"] == m])
                      for m in markets},
        "by_strategy": {f"{k[0]}|{k[1]}": score(v) for k, v in groups.items()},
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4)
    print(f"\nSaved to {args.out}")


if __name__ == "__main__":
    main()
