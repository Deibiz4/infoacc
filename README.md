# ⚡ InfoAcc - Autonomous Market Intelligence & Trading Analytics Hub

[![Daily Report Automation](https://github.com/Deibiz4/infoacc/actions/workflows/daily_report.yml/badge.svg)](https://github.com/Deibiz4/infoacc/actions/workflows/daily_report.yml)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![Live Hub](https://img.shields.io/badge/Web_Hub-Live_Online-00f2fe.svg)](https://deibiz4.github.io/infoacc/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**InfoAcc** is an automated, institutional-grade daily market intelligence and quantitative trading analytics system. It scans financial markets every morning, performs technical & sentiment analysis, generates interactive daily reports for **Stocks**, **Cryptocurrencies**, and **Forex**, tracks signal performance in real time, and publishes a live analytics hub.

🌐 **Live Web Application:** [https://deibiz4.github.io/infoacc/](https://deibiz4.github.io/infoacc/)

---

## ✨ Key Features

- **🌐 Multi-Market Quantitative Coverage:**
  - **Stocks Market:** S&P 500, Nasdaq-100, momentum breakouts, and RSI oversold/overbought value setups.
  - **Crypto Market:** BTC, ETH, and major Altcoins with real-time on-chain risk sentiment.
  - **Forex Market:** Major currency pairs & crosses integrated with DXY strength tracking.

- **📊 Real-Time Analytics & Performance Dashboard (`analytics.html`):**
  - **Win Rate & Profit Factor:** Automated tracking of win percentage, loss ratio, and profit factor.
  - **Risk-Adjusted Equity Curve:** Cumulative R-unit growth curve plotted dynamically using [Chart.js](https://www.chartjs.org/).
  - **Full Signal Audit:** Audit table tracking every pending, active, target-hit, and stop-loss hit signal.

- **📈 Interactive TradingView Lightweight Charts:**
  - Each signal card in daily HTML reports embeds an interactive [TradingView Lightweight Chart](https://www.tradingview.com/lightweight-charts/).
  - Dynamically renders **Entry (Blue)**, **Take Profit (Green)**, and **Stop Loss (Red)** levels directly on the price chart.

- **🧠 Market Sentiment & High-Impact Macro Calendar:**
  - **Crypto Fear & Greed Index:** Real-time sentiment classification fetched from Alternative.me.
  - **Stock Volatility Sentiment:** Calculated using the VIX Volatility Index.
  - **Macro Economic Calendar:** Automated detection of key economic events (FOMC FED decisions, CPI inflation reports, NFP Friday payrolls, ECB rate announcements).

- **☁️ 100% Cloud-Autonomous Pipeline (GitHub Actions):**
  - Runs automatically every weekday at **07:00 AM UTC** via `.github/workflows/daily_report.yml`.
  - Scans data, updates Google Sheets (optional via secret), generates fresh HTML reports, updates Analytics datasets, and deploys directly to GitHub Pages.

---

## 🤖 System Architecture & AI Strategy

InfoAcc uses a **hybrid deterministic quantitative engine** paired with **institutional-grade AI prompt engineering guidelines**:

- **⚡ Deterministic Quantitative Core (0% API Overhead & 0% AI Hallucinations):**
  - All market scans, price levels, RSI/EMA indicators, ATR targets, Stop Losses, and Win Rate calculations are processed in **pure Python**.
  - Ensures **100% mathematical accuracy** without numeric hallucinations or latency. Runs completely free on GitHub Actions.

- **📜 Institutional AI Prompt Guidelines (`report_generation_prompt.md`):**
  - Contains structured master prompts designed following **Goldman Sachs, Morgan Stanley, and J.P. Morgan Equity Research** standards.
  - Formatted for seamless integration with LLMs (such as OpenAI GPT-4o or Google Gemini 1.5 Pro) if narrative synthesis or executive summary extensions are enabled.

---

## 🏛️ Application Navigation

| Module | URL | Description |
| :--- | :--- | :--- |
| **⚡ Main Hub** | [index.html](https://deibiz4.github.io/infoacc/index.html) | Central repository for daily market reports & archives. |
| **📊 Analytics** | [analytics.html](https://deibiz4.github.io/infoacc/analytics.html) | Win Rate %, Profit Factor & Equity Curve dashboard. |
| **📈 Signals Monitor** | [signals.html](https://deibiz4.github.io/infoacc/signals.html) | Real-time signal tracker for open & pending setups. |

---

## 📂 Project Structure

```text
infoacc/
├── .github/
│   └── workflows/
│       └── daily_report.yml       # GitHub Actions automated 7:00 AM workflow
├── data/
│   ├── analytics.json             # Consolidated performance metrics & equity curve
│   ├── market_scan.csv            # Raw technical scanner output
│   └── signals.json               # Active, pending, and historical stock signals
├── infocryptos/                   # Dedicated Cryptocurrency market module
│   ├── data/                      # Crypto signals & scanner data
│   ├── reports/                   # Daily Crypto HTML & MD reports
│   └── scripts/                   # Crypto scanner, generator & hub updater
├── infofx/                        # Dedicated Forex currency market module
│   ├── data/                      # Forex signals & scanner data
│   ├── reports/                   # Daily Forex HTML & MD reports
│   └── scripts/                   # Forex scanner, generator & hub updater
├── reports/                       # Daily Stocks HTML & MD reports
├── scripts/
│   ├── fetch_calendar.py          # High-impact economic calendar detector
│   ├── fetch_sentiment.py         # Crypto Fear & Greed & VIX sentiment calculator
│   ├── generate_analytics.py      # Win Rate, Profit Factor & Equity Curve generator
│   ├── market_scanner.py          # Technical scanner (RSI, EMAs, ATR, S/R)
│   ├── report_generator.py        # HTML report generator with TradingView charts
│   ├── track_signals.py           # Real-time price crossing & SL/TP tracker
│   ├── update_history.py          # Google Sheets history consolidator
│   └── update_hub.py              # Web hub index.html synchronizer
├── analytics.html                 # Interactive Analytics Dashboard
├── index.html                     # Web Hub home page
├── master_workflow.py             # Main orchestrator script
├── schedule_task.ps1              # Windows Task Scheduler registrar (7:00 AM)
├── worker.py                      # Continuous Python scheduler background worker
├── Dockerfile                     # Container definition
├── docker-compose.yml             # Web server & worker container compose file
└── requirements.txt               # Python dependencies
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Dependencies listed in `requirements.txt`

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Deibiz4/infoacc.git
   cd infoacc
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## ⚙️ Usage

### Run the Full Master Workflow Manually

To trigger immediate scanning, signal tracking, report generation, analytics consolidation, and hub updating:

```bash
python master_workflow.py
```

### Run Continuous Background Worker (Local)

To run the Python scheduler in the background (triggers Mon-Fri at 07:00 AM):

```bash
python worker.py
```

Or run via `pythonw` on Windows (no console window):

```cmd
start pythonw worker.py
```

### Schedule Native Windows Task

Run PowerShell as Administrator to register a Windows Scheduled Task named `DailyMarketReport`:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
.\schedule_task.ps1
```

### Run Containerized with Docker

```bash
docker-compose up -d --build
```

---

## 🔐 Environment & Google Sheets Integration

Google Sheets integration is **optional**. The system generates all reports, interactive charts, and analytics dashboards using public market APIs (`yfinance`, `alternative.me`) without requiring credentials.

If you wish to synchronize historical signals with a Google Sheet:

1. Place your Google Service Account key file named `credentials.json` in the project root directory.
2. For GitHub Actions cloud executions, paste the raw contents of `credentials.json` into **GitHub Repository Secrets** under the name **`GOOGLE_CREDENTIALS`**.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
