# 🛡️ Risk Assessment Engine v1

<p align="center">
  <strong>The Final Gatekeeper & Portfolio Protection Engine for the Alpaca AI Hackathon 2026</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Layer-Agentic%20Layer-blue" alt="Agentic Layer">
  <img src="https://img.shields.io/badge/Component-Risk%20Engine-purple" alt="Risk Assessment Engine">
  <img src="https://img.shields.io/badge/Python-3.10%2B-yellow" alt="Python">
  <img src="https://img.shields.io/badge/Status-Active-success" alt="Status">
</p>

---

## 📌 Overview

The **Risk Assessment Engine** is the ultimate safety net of the **Agentic Layer**.

Its job is simple but critical:

> **Receive qualitative trade proposals, autonomously fetch live portfolio state from Alpaca, calculate precise quantitative contract sizing based on buying power and risk budgets, strictly enforce mathematical risk limits, and decisively output a PASS or REJECT signal.**

The engine bypasses the LLMs entirely and serves as the single quantitative authority. It relies on pure, deterministic Python math to evaluate the economic reality of a trade against the global `User_Config`. The engine calculates exactly how many contracts are permitted. If it breaches daily loss or portfolio exposure limits, it completely rejects the trade.

The final output is a JSON payload containing:

- ⚖️ Decision (`PASS` or `REJECT`)
- 📉 Risk Metrics (Max Loss, Max Profit, Breakeven)
- 📊 Detailed Checks (RR, Buying Power, Portfolio Exposure, Daily Loss)
- ✂️ Adjustments (e.g., downsizing oversized position proposals)
- 🛑 Rejection Reasons (if applicable)

---

## 🔄 Agentic Layer Flow

```text
                  ┌─────────────────────────────┐
                  │        AGENTIC LAYER
                  |                             │
                  │ ┌─────────┬─────────┬─────┐ │
                  │ ▼         ▼         ▼     │ │
                  │NEWS    MARKET    OPTIONS  │ │
                  │AGENT    AGENT     AGENT   │ │
                  │ │         │         │     │ │
                  │ └─────────┼─────────┘     │ │
                  │           ▼               │ │
                  │   🧠 DECISION AGENT       │ │
                  │           │               │ │
                  │           ▼               │ │
                  │ 🛡️ RISK ASSESSMENT ENGINE │ │
                  │           │               │ │
                  │           ▼               │ │
                  │ 🚀 EXECUTION AGENT        │ │
                  └───────────┼───────────────┘
                              │
                        ┌─────┴─────┐
                        ▼           ▼
                   LIVE TRADE      Reject
```

### What each component does

| Component | Responsibility |
|---|---|
| 🔎 **Deterministic Filter** | Finds and ranks promising assets |
| 🤖 **Market Agent** | Analyzes technical market conditions |
| 📰 **News Agent** | Analyzes news and sentiment |
| 📊 **Options Agent** | Analyzes possible options strategies |
| 🧠 **Decision Agent** | Combines outputs to formulate a trading plan |
| 🛡️ **Risk Engine** | Validates trade against portfolio risk rules |
| 🚀 **Execution Agent** | **Executes the live trade on Alpaca** |

---

# 🎯 What Does the Risk Engine Do?

The Risk Engine acts as the final mathematical gatekeeper:

```text
               DECISION AGENT
               (Trade Proposal)
                      │
                      ▼
             ALPACA TRADING API
        (Fetch Equity & Positions)
                      │
                      ▼
         PYTHON MATH & RISK LIMIT CHECKS
            1. Max Trade Risk Sizing
            2. Portfolio Capital Exposure
            3. Daily Drawdown Limit
            4. Buying Power Validation
                      │
                      ▼
            PASS OR REJECT VERDICT
             (Final JSON Output)
```

---

# 📥 Input Format

The Risk Engine requires the **Trade Proposal** from the Decision Agent. It fetches the account context (like current equity and positions) itself.

```json
{
  "symbol": "AAPL",
  "strategy": {
    "type": "Bull Call Spread",
    "legs": [
      {
        "action": "BUY",
        "option_type": "CALL",
        "strike": 171.99,
        "price": 3.60
      },
      {
        "action": "SELL",
        "option_type": "CALL",
        "strike": 184.275,
        "price": 1.20
      }
    ]
  },
  "proposed_contracts": 4
}
```

---

# 🧠 Analysis Logic

The Risk Engine uses deterministic math to strictly enforce four core rules:

## 1. Data Fetching (Alpaca)
The engine automatically queries Alpaca using the `alpaca-py` SDK to pull:
- `equity` (Current account value)
- `last_equity` (Start-of-day baseline)
- `buying_power` 
- `positions` (To calculate existing committed capital)

## 2. Max Trade Risk (Auto-Sizing)
- Evaluates the max loss per contract against the user's `max_risk_per_trade_pct`.
- **Auto-Adjustment:** If the requested contracts exceed the risk limit, the engine automatically downsizes the trade using `math.floor()`.

## 3. Portfolio Capital Exposure
- Aggregates the `cost_basis` of all active Alpaca positions and adds the capital requirement of the new trade.
- Checks if the total committed capital breaches `max_exposure_pct`.

## 4. Daily Loss Limit
- Calculates the current account drawdown (`last_equity - equity`).
- Adds the potential max loss of the new trade to the drawdown.
- Rejects the trade if the combined figure exceeds `max_daily_loss_pct`.

## 5. Buying Power & Open Positions
- Validates the trade's capital requirement against available buying power.
- Ensures the total count of open positions will not exceed `max_open_positions`.

---

# 📤 Output Format

The engine formats its final verdict as a strict JSON document.

### Example: PASS (With Sizing Adjustment)

```json
{
  "decision": "PASS",
  "symbol": "AAPL",
  "strategy": "Bull Call Spread",
  "risk": {
    "max_loss_per_contract": 240.0,
    "max_loss_total": 960.0,
    "max_profit_per_contract": 988.5,
    "max_profit_total": 3954.0,
    "risk_reward_ratio": 4.12,
    "breakeven": 174.39
  },
  "checks": {
    "max_risk_per_trade": "PASS",
    "risk_reward": "PASS",
    "portfolio_exposure": "PASS",
    "buying_power": "PASS",
    "open_positions": "PASS",
    "daily_loss_limit": "PASS"
  },
  "order": {
    "contracts": 4,
    "limit_price": 2.4
  },
  "adjustments": [
    "Position size reduced from 6 to 4 contracts to comply with maximum risk."
  ]
}
```

### Example: REJECT

```json
{
  "decision": "REJECT",
  "symbol": "AAPL",
  "strategy": "Bull Call Spread",
  "checks": {
    "max_risk_per_trade": "PASS",
    "portfolio_exposure": "FAIL",
    "buying_power": "PASS",
    "daily_loss_limit": "PASS"
  },
  "rejection_reasons": [
    "Projected portfolio capital exposure $20460.00 exceeds limit of $20000.00."
  ]
}
```

---

# 🚫 What the Risk Engine Does NOT Do

The Risk Engine is responsible for **math and validation only**.

It does **not**:

- ❌ Talk to Large Language Models (LLMs).
- ❌ Decide *what* to trade. (That's the Decision Agent)
- ❌ Formulate strategy strikes. (That's the Options Agent)

---

# 🚀 Quick Start

## 1. Install Dependencies

```bash
pip install -r ../requirements.txt
```

## 2. Configure Environment

The project relies on a shared `.env` file situated at the root directory of the repository (`../.env`).

```env
APCA_API_KEY_ID=your_alpaca_key
APCA_API_SECRET_KEY=your_alpaca_secret
```

## 3. Run the Agent

You can safely run the engine to execute the built-in mock tests without needing live Alpaca keys.

```bash
python risk_engine.py
```

---

# 📁 Project Structure

```text
Risk Assessment Engine/
│
├── risk_engine.py
└── readme.riskengine.md
```

---

# 🛠️ Dependencies

| Package | Purpose |
|---|---|
| `alpaca-py` | Natively fetching real-time account data and positions |
| `python-dotenv` | Loading keys from the shared root `.env` |
| `math` & `json` | Core mathematical processing and output formatting |

---

# 👨‍💻 Team Responsibility

| Component | Developer |
|---|---|
| 🔎 Deterministic Filter | M-Rohan-Sohail |
| 🤖 Market Agent | Subhan-Developer |
| 📰 News Agent | Team Member |
| 📊 Options Agent | Team Member |
| 🧠 Decision Agent | Team Member |
| 🛡️ **Risk Engine** | **Team Member** |

---

# 🧠 In Simple Words

The Risk Assessment Engine is basically your **Automated Chief Risk Officer (CRO)**.

It answers one main question:

> **"Regardless of what the AI agents decided, does this trade mathematically break our account's risk limits? If so, shrink it or kill it."**

---

## 🏆 Project

**Alpaca AI Hackathon 2026**

**Layer:** Agentic Layer  
**Component:** Risk Assessment Engine
