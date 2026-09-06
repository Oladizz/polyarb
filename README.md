<div align="center">

# 🦅 PolyArb

**Autonomous Polymarket Quant Intelligence, Combinatorial Arbitrage Scanner & Research Engine**

[![Python 3.12](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker Ready](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](Dockerfile)
[![Deploy to Render](https://img.shields.io/badge/Deploy%20to-Render-46E3B7?logo=render&logoColor=white)](render.yaml)
[![Deploy on Railway](https://img.shields.io/badge/Deploy%20on-Railway-0B0D0E?logo=railway&logoColor=white)](railway.json)

[Overview](#-overview) • [Autonomous Trading Engine](#-autonomous-trading-engine) • [The 3 Core Inefficiencies](#-the-3-core-inefficiencies) • [Live Dashboard](#-live-web-dashboard) • [Telegram Bot](#-telegram-bot) • [Quickstart](#-quickstart)

</div>

---

## 📖 Overview

**PolyArb** is an automated quant intelligence and execution harness designed specifically for **Polymarket** (Polygon POS + Gnosis Conditional Token Framework + UMA Optimistic Oracle).

Unlike naive bots that try to "guess" event winners with language models, **PolyArb exploits structural, mathematical, and settlement friction**:

```
                       ┌──► Negative-Risk Combinatorial Arbitrage (∑P ≠ 1.00)
                       │
[Polymarket Telemetry] ┼──► Resolution Lag Yields (Decided Tokens @ 98.0¢ - 99.0¢)
  (Gamma + CLOB API)   │
                       ├──► Merkl Liquidity Mining & Spread Rebates
                       │
                       └──► Deep Quant Web Research & PDF Dossier Compiler
```

---

---

## ⚡ Autonomous Trading Engine

PolyArb features a production-grade automated trading daemon that runs 24/7 in an event loop:

* **Continuous Live Market Ingestion:** Polls Polymarket CLOB and Gamma feeds at configurable intervals.
* **UMA Oracle Dispute Filter:** Passes every candidate market through [`OracleAuditor`](file:///home/rabiuoladizz/polyarb/app/scanner/oracle_audit.py) to reject ambiguous resolution rules or disputed questions.
* **Capital Allocation & Position Sizing:** Enforces maximum capital per position, portfolio diversification, and fee/slippage buffers.
* **Settlement Tracking:** Monitors active holdings until market resolution, settles winning tokens, and credits realized PnL.
* **State Persistence:** Saves portfolio equity, active positions, and trade history across restarts (`data/portfolio.json`).

```bash
# Run one execution cycle and display portfolio impact
python cli.py --trade --cycles 1

# Run the 24/7 continuous autonomous trading daemon (30s interval)
python cli.py --trade --interval 30 --mode paper

# View active positions and portfolio equity
python cli.py --portfolio
```

## ⚡ The 3 Core Inefficiencies

### 1. Negative-Risk Combinatorial Arbitrage ($\sum P \neq 1.00$)
In mutually exclusive multi-outcome events (e.g. tournament champions, elections), the mathematical sum of all "YES" token prices must equal **$1.00**:
* **When $\sum P < 0.985$ (Mint Discount):** Buying 1 share of every candidate costs less than $1.00. Because one outcome is guaranteed to win, the basket redeems on-chain for $1.00, securing a guaranteed profit.
* **When $\sum P > 1.015$ (Overpriced Basket):** Deposit $1.00 USDC into Gnosis CTF `splitPosition` to mint full token sets and sell them into bids, capturing the spread.

### 2. Resolution Lag Settlement Discounting
When an event has physically concluded in real life, UMA Oracle has a **2 to 48-hour liveness and dispute window** before funds unlock:
* Retail traders frequently dump winning shares at **98.0¢ to 99.0¢** to redeploy their capital immediately.
* PolyArb sweeps these discounted tokens. Earning a 1.5% profit over a 24-hour settlement window equals an **annualized APY of >500%** with zero directional market risk.

### 3. Liquidity Mining & Maker Rebate Farming
* Polymarket distributes thousands in daily USDC rewards via Merkl to market makers who maintain bid-ask spreads within `rewardsMaxSpread`.
* PolyArb identifies low-volatility pairs with maximum reward distribution to farm passive yields with delta-neutral inventory.

---

## 🖥️ Live Web Dashboard

PolyArb includes an integrated dark-mode web terminal:

```bash
python main.py
# Open http://localhost:8080
```

* **Live Arbitrage Terminal:** Real-time matrix of active multi-outcome pricing gaps and settlement yields.
* **Paper Trading Dashboard:** Visual tracking of virtual portfolio balance, win rate, and realized PnL.
* **One-Click Quant Dossier:** Compiles full research summaries and downloads styled WeasyPrint PDF reports.

---

## 🤖 Telegram Bot Daemon

Control PolyArb directly from your phone:

```bash
export TELEGRAM_BOT_TOKEN="your-bot-token"
python cli.py --daemon
```

### Supported Commands:
* `/scan` — Comprehensive live scan across active Polymarket order books.
* `/negrisk` — Shows live combinatorial mispricings where $\sum P \neq 1.00$.
* `/reslag` — Shows decided high-probability tokens trading at settlement discounts.
* `/rewards` — Shows top liquidity mining pools and reward spreads.
* `/research [topic]` — Generates a deep quant intelligence report and uploads the PDF dossier directly into the chat!
* `/paper` — Displays current simulated portfolio performance and win rate.
* `/simulate` — Automatically paper-trades the best active opportunity right now.

---

## 🚀 Quickstart

### 1. Installation
```bash
git clone https://github.com/Oladizz/polyarb.git
cd polyarb

pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Run Live Scan (CLI)
```bash
python cli.py --scan
```

### 3. Generate Quant Loophole Research Dossier
```bash
python cli.py --research "polymarket arbitrage loopholes"
# Output: polyarb_research_report.md & polyarb_research_report.pdf
```

### 4. Run Test Suite
```bash
pytest tests/ -v
```

---

## 🧪 Testing & Verification

The repository includes a comprehensive unit test suite covering:
* Combinatorial arbitrage math and slippage buffers
* Resolution lag discounting and APY calculations
* Paper trading portfolio simulation
* WeasyPrint PDF generation and REST endpoints

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
