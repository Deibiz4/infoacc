"""Rebuild the signal history so the published metrics are measurable.

Three things are wrong with the accumulated signals.json files:

  1. Duplicates. The scanner used to re-emit a signal for a ticker whose earlier
     signal had already been closed the same day, so the same trade was counted
     several times.
  2. Mixed engines. Signals from before the strategy overhaul are scored
     alongside the current engine, which makes the headline numbers describe a
     strategy that no longer exists.
  3. Statuses derived by the old tracker, which resolved signals against candles
     that predate them.

This rebuilds the files: dedupes on (ticker, date), moves pre-overhaul signals
to an archive, and re-derives every status from real price history using the
current rules in track_signals.resolve_signal.

Run with --dry-run first to see what it would do.
"""
import argparse
import json
import os
import sys
import warnings

warnings.filterwarnings("ignore")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

import pandas as pd
import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from track_signals import get_yf_ticker, resolve_signal

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MARKETS = {
    "Stocks": os.path.join(BASE_DIR, "data"),
    "Crypto": os.path.join(BASE_DIR, "infocryptos", "data"),
    "Forex": os.path.join(BASE_DIR, "infofx", "data"),
}

# The engine overhaul (commit c2d8868) landed 2026-07-24 09:57 CEST, after that
# day's 08:45 run. The first scan using the new rules was therefore 2026-07-27.
ENGINE_V2_START = "2026-07-27"


def dedupe(signals):
    """Keep the first signal per (ticker, date); the rest are re-emissions."""
    seen, kept, dropped = set(), [], []
    for s in signals:
        key = (s.get("ticker"), s.get("date"))
        if key in seen:
            dropped.append(s)
            continue
        seen.add(key)
        kept.append(s)
    return kept, dropped


def fetch_history(tickers, start):
    if not tickers:
        return {}
    data = yf.download(
        tickers, start=start, group_by="ticker", progress=False, auto_adjust=False
    )
    frames = {}
    for t in tickers:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                # yfinance keeps a (ticker, field) MultiIndex even for a single
                # ticker, so always select by level rather than assuming shape.
                level = 0 if t in data.columns.get_level_values(0) else 1
                df = data.xs(t, level=level, axis=1)
            else:
                df = data
            df = df.dropna(how="all")
        except Exception:
            continue
        if not df.empty and "High" in df.columns:
            frames[t] = df
    return frames


def rebuild_market(market, data_dir, dry_run):
    path = os.path.join(data_dir, "signals.json")
    if not os.path.exists(path):
        print(f"  {market}: no signals.json, skipping.")
        return None

    with open(path, "r", encoding="utf-8") as f:
        signals = json.load(f)

    original = len(signals)
    signals, dupes = dedupe(signals)

    archive = [s for s in signals if s.get("date", "") < ENGINE_V2_START]
    current = [s for s in signals if s.get("date", "") >= ENGINE_V2_START]

    # Re-derive statuses from scratch: every signal starts PENDING again and is
    # replayed against real prices with the corrected rules.
    earliest = min((s.get("date", "") for s in current), default=None)
    frames = {}
    if current and earliest:
        yf_tickers = sorted({get_yf_ticker(s.get("ticker")) for s in current})
        print(f"  {market}: fetching prices for {len(yf_tickers)} tickers from {earliest}...")
        frames = fetch_history(yf_tickers, earliest)

    changed = 0
    for s in current:
        before = s.get("status")
        df = frames.get(get_yf_ticker(s.get("ticker")))
        s["status"] = resolve_signal(s, df, start_status="PENDING")
        if s["status"] != before:
            changed += 1

    print(
        f"  {market}: {original} -> {len(current)} signals "
        f"({len(dupes)} duplicates removed, {len(archive)} archived as v1, "
        f"{changed} statuses corrected)"
    )

    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=4)
        if archive:
            archive_path = os.path.join(data_dir, "signals_archive_v1.json")
            with open(archive_path, "w", encoding="utf-8") as f:
                json.dump(archive, f, indent=4)

    return current


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Report without writing")
    args = parser.parse_args()

    mode = " (DRY RUN)" if args.dry_run else ""
    print(f"=== REBUILDING SIGNAL HISTORY{mode} ===")
    print(f"Engine v2 cutoff: {ENGINE_V2_START}\n")

    for market, data_dir in MARKETS.items():
        rebuild_market(market, data_dir, args.dry_run)

    print("\n=== DONE ===")
    if args.dry_run:
        print("Nothing written. Re-run without --dry-run to apply.")
    else:
        print("Run scripts/generate_analytics.py to refresh the published metrics.")


if __name__ == "__main__":
    main()
