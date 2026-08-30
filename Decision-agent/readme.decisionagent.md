# 🧠 Decision Agent v1

<p align="center">
  <strong>The Final Orchestrator & Risk Engine for the Alpaca AI Hackathon 2026</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Layer-Agentic%20Layer-blue" alt="Agentic Layer">
  <img src="https://img.shields.io/badge/Component-Decision%20Agent-purple" alt="Decision Agent">
  <img src="https://img.shields.io/badge/Python-3.10%2B-yellow" alt="Python">
  <img src="https://img.shields.io/badge/Status-Active-success" alt="Status">
</p>

---

## 📌 Overview

The **Decision Agent** is the final and most critical component of the **Agentic Layer**.

Its job is simple but critical:

> **Aggregate outputs from all upstream agents and qualitatively evaluate the strategy using an LLM to formulate a coherent TRADE or PASS decision.**

The agent acts as the qualitative evaluator. It ensures that the market, news, and options signals are perfectly aligned before passing its proposal to the Risk Assessment Engine for strict quantitative sizing and risk validation.

---

## 🔄 Agentic Layer Flow

```text
                         🔎 DETERMINISTIC FILTER
                                │
                         Selects Candidates
                                │
                                ▼
                 ┌─────────────────────────────┐
                 │        AGENTIC LAYER        │
                 │                             │
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
                     TRADE        PASS
```

### What each component does

| Component | Responsibility |
|---|---|
| 🔎 **Deterministic Filter** | Finds and ranks promising assets |
| 🤖 **Market Agent** | Analyzes technical market conditions |
| 📰 **News Agent** | Analyzes news and sentiment |
| 📊 **Options Agent** | Analyzes possible options strategies |
| 🧠 **Decision Agent** | Combines all agent outputs and decides TRADE/PASS |

---

# 🎯 What Does the Decision Agent Do?

The Decision Agent operates in a robust **Two-Step Pipeline**:

### Step 1: Qualitative LLM Reasoning
It feeds the outputs of the Market, News, and Options Agents, alongside your live Alpaca portfolio data, into a large language model. The LLM acts as a Senior Portfolio Manager to check directional alignment, detect contradictions, and provide a qualitative `TRADE` or `PASS` decision.

### Step 2: Quantitative Python Validation
It strips away the LLM's assumptions and deterministically calculates the risk mathematically using raw Python. 
- It calculates Max Loss, Max Profit, and Breakeven directly from the option legs.
- It sizes the trade based on **3 strict limits**:
  1. **Trade Allocation:** Max 5% of Portfolio Equity.
  2. **Total Exposure:** Existing Exposure + New Trade ≤ 20%.
  3. **Account Risk:** Existing Risk + New Trade Risk ≤ 1%.

If a trade breaches a limit, the Python engine will aggressively resize it downwards. If it hits 0 contracts, the trade is rejected.

---

# 📥 Input Sources

The Decision Agent dynamically loads and parses the latest outputs from:

1. `Market Agent Output/*.json` (Market conditions & Direction)
2. `News Agent Output/*.json` (News Sentiment & Catalysts)
3. `Options Agent Output/*.json` (Proposed Options Strategies)
4. **Alpaca API** (Live Portfolio Equity, Cash, and Positions)

---

# 📤 Output Format

The `decide()` function returns a structured JSON object containing an array of decisions, and automatically saves it to the `Decision Agent Output/` directory.

```json
{
  "run_timestamp": "20260827_174702",
  "decisions": [
    {
      "symbol": "AAPL",
      "decision": "TRADE",
      "direction": "BULLISH",
      "strategy": {
        "type": "Bull Call Spread",
        "legs": [
          {
            "symbol": "AAPL260926C00171990",
            "action": "BUY",
            "option_type": "CALL",
            "strike": 171.99,
            "expiration": "2026-09-26",
            "price": 3.6
          },
          {
            "symbol": "AAPL260926C00184275",
            "action": "SELL",
            "option_type": "CALL",
            "strike": 184.275,
            "expiration": "2026-09-26",
            "price": 1.2
          }
        ]
      },
      "confidence": 0.90,
      "reasoning": "Strong technical momentum backed by product launch news.",
      "risk_assessment": {
        "status": "ACCEPTABLE",
        "approved_contracts": 4,
        "max_loss_per_contract": 240.0,
        "max_profit_per_contract": 988.0,
        "risk_reward_ratio": 4.12,
        "breakeven": 174.39
      }
    }
  ]
}
```

### Output Fields

| Field | Type | Description |
|---|---|---|
| `symbol` | `string` | Stock that was analyzed |
| `decision` | `string` | `TRADE` or `PASS` |
| `strategy` | `object` | The options legs executed |
| `risk_assessment` | `object` | Approved contracts and exact calculated risk metrics |

---

# 🚫 What the Decision Agent Does NOT Do

The Decision Agent acts as the final strategic brain, but it does **not**:

- ❌ Act as the execution broker directly. (It approves the contracts, but hands them off to an execution layer).
- ❌ Guess math. All R/R and Breakeven calculations are strictly computed in Python.

---

# 🚀 Quick Start

## 1. Install Dependencies

```bash
pip install -r requirements.txt
pip install alpaca-py
```

## 2. Configure Environment

Create a `.env` file inside the directory:

```env
GROQ_API_KEY=your-groq-key
ALPACA_API_KEY=your-alpaca-key
ALPACA_SECRET_KEY=your-alpaca-secret
ALPACA_PAPER=True
```

## 3. Run the Agent Standalone

```bash
python3 decision_agent.py
```

Example output:

```text
🚀 Decision Agent Test
==================================================
2026-08-27 17:36:21 - INFO - ✅ Alpaca client initialized
2026-08-27 17:36:21 - INFO - ✅ Groq client initialized
2026-08-27 17:36:21 - INFO - 🤔 DecisionAgent starting run for symbols: ['NVDA', 'AAPL', 'MSFT']
2026-08-27 17:36:22 - ERROR - ❌ Incomplete Data for NVDA: Data for NVDA not found across all 3 agent outputs.
2026-08-27 17:36:25 - INFO - ✅ AAPL: TRADE approved for 4 contracts.
2026-08-27 17:36:27 - INFO - ✅ MSFT: TRADE approved for 4 contracts.
2026-08-27 17:36:27 - INFO - 💾 Saved Decision Agent output to /home/.../Decision Agent Output/decision_analysis_20260827_173627.json
```

---

# 👨‍💻 Team Responsibility

| Component | Developer |
|---|---|
| 🔎 Deterministic Filter | M-Rohan-Sohail |
| 🤖 Market Agent | Subhan-Developer |
| 📰 News Agent | Team Member |
| 📊 Options Agent | Team Member |
| 🧠 **Decision Agent** | **Team Member** |

---

# 🧠 In Simple Words

The Decision Agent is basically your **Risk Manager**.

It answers one main question:

> **"Does this trade make sense given the market and news context, and is it mathematically safe enough for my portfolio?"**

```text
 📊 Agent Outputs (Market/News/Options) + 💰 Live Alpaca Portfolio
       ↓
 🧠 Qualitative LLM Check (Does it make sense?)
       ↓
 🧮 Python Risk Math (Does it blow up my account?)
       ↓
 ┌─────────────┬─────────────┐
 │ ✅ TRADE   │ ❌ PASS     │
 └─────────────┴─────────────┘
       ↓
 📝 Approved Contracts & Risk Summary
```

---

## 🏆 Project

**Alpaca AI Hackathon 2026**

**Layer:** Agentic Layer  
**Component:** Decision Agent
