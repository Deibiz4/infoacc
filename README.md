# InfoAcc - Automated Market Reporting System

InfoAcc is an automated system designed to generate comprehensive daily market reports for Stocks, Cryptocurrencies, and Forex. It orchestrates data gathering, analysis, and report generation, publishing the results to a web hub.

## Features

- **Multi-Market Coverage**: Generates reports for Stocks, Crypto, and Forex.
- **Automated Workflow**:
  - `master_workflow.py`: The main entry point that triggers report generation for all markets and updates historical data.
  - `daily_workflow.py`: Handles the specific logic for data scanning, processing, and report generation for each market segment.
- **Data Analysis**: Scans markets for signals and trends using custom scripts (`market_scanner.py`, `update_history.py`).
- **Web Integration**: Updates a central web hub (`index.html`) with the latest reports.
- **Dockerized**: specific `Dockerfile` and `docker-compose.yml` for easy deployment.

## Project Structure

- `master_workflow.py`: Main Orchestrator script.
- `daily_workflow.py`: specific workflow for daily report generation.
- `infocryptos/`: Specific configurations/scripts for Cryptocurrency reports.
- `infofx/`: Specific configurations/scripts for Forex reports.
- `scripts/`: Helper scripts for data scanning, history updates, and hub management.
- `reports/`: Generated HTML and Markdown reports.
- `data/`: Temporary data storage for scans and signals.

## Getting Started

### Prerequisites

- Python 3.x
- Docker (optional, for containerized run)
- Dependencies listed in `requirements.txt`

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Deibiz4/infoacc.git
   cd infoacc
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Usage

**Run the full workflow:**

```bash
python master_workflow.py
```

**Run a specific market workflow:**

You can run `daily_workflow.py` independently if needed, though `master_workflow.py` is the recommended entry point.

**Run with Docker:**

```bash
docker-compose up --build
```

## Configuration

Ensure you have the necessary credentials (e.g., `credentials.json` for Google services if used) placed in the root directory. These are excluded from the repository for security.

## License

[MIT](LICENSE)
