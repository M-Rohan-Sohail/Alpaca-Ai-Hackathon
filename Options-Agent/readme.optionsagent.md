# 📊 Options Agent v1

<p align="center">
  <strong>AI-powered multi-leg options strategy formulation for the Alpaca AI Hackathon 2026</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Layer-Agentic%20Layer-blue" alt="Agentic Layer">
  <img src="https://img.shields.io/badge/Component-Options%20Agent-purple" alt="Options Agent">
  <img src="https://img.shields.io/badge/Python-3.10%2B-yellow" alt="Python">
  <img src="https://img.shields.io/badge/Status-Active-success" alt="Status">
</p>

---

## 📌 Overview

The **Options Agent** is an AI-powered component of the **Agentic Layer**.

Its job is simple:

> **Dynamically aggregate candidate data across the pipeline, fetch live options chains from Alpaca, formulate a strategic options play using an LLM, and rigorously calculate risk/reward metrics using Python.**

The agent uses the Alpaca API to fetch options chains, passes the filtered data to Groq's LLM to generate a structured strategy, and then mathematically validates that strategy for realistic execution. The final proposal contains:

- 🎯 Specific Strategy Type (e.g., Bull Call Spread, Iron Condor)
- 🛒 Specific Legs (Strikes, Expirations, Buy/Sell Actions)
- 💰 Realistic Execution Prices (Bid/Ask)
- 📈 Risk/Reward Metrics (Max Profit, Max Loss, Breakeven, Net Debit/Credit)
- 🧠 Reasoning

The result is saved to disk where it can be picked up by the **Decision Agent**.

---

## 🔄 Agentic Layer Flow

```text
                         🔎 MARKET SCANNER
                                │
                         Selects Candidates
                                │
                                ▼
                 ┌─────────────────────────────┐
                 │        AGENTIC LAYER
                 |                             │
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
                 └───────────┼───────────────┘
                             │
                       ┌─────┴─────┐
                       ▼           ▼
                     TRADE        Reject
```

### What each component does

| Component | Responsibility |
|---|---|
| 🔎 **Market Scanner** | Finds and ranks promising assets |
| 🤖 **Market Agent** | Analyzes technical market conditions |
| 📰 **News Agent** | Analyzes news and sentiment |
| 📊 **Options Agent** | Analyzes possible options strategies |
| 🧠 **Decision Agent** | Combines all agent outputs and decides TRADE/PASS |

---

# 🎯 What Does the Options Agent Do?

The Options Agent acts as a central aggregator and strategist:

```text
      MARKET SCANNER   NEWS AGENT    DATA PROCESSING 
             │              │               │
             └──────────────┼───────────────┘
                            ▼
                     DATA AGGREGATION
                            │
                            ▼
                  ALPACA OPTIONS API
                     (Fetch Chain)
                            │
                            ▼
              PYTHON LIQUIDITY PRE-FILTER
           (Spread limits, OI/Vol limits, DTE)
                            │
                            ▼
                  GROQ LLM STRATEGIST
               (Formulates Strategy Legs)
                            │
                            ▼
             PYTHON MATH & VALIDATION ENGINE
          (Calculates Max PNL, Checks Spreads)
                            │
                            ▼
               FINAL OPTIONS STRATEGY JSON
```

---

# 📥 Input Format

The Options Agent automatically polls the latest timestamped output files from the other components. It merges:
1. The **Market Scanner** output (for symbols and core scores).
2. The **News Agent** output (for sentiment news).
3. The **Data Processing** layer (for price, RSI, ATR, and returns).

It dynamically constructs an internal payload for each candidate that looks like this:

```json
{
  "symbol": "NVDA",
  "price": 180.45,
  "scores": {
    "opportunity": 93.2,
    "momentum": 100,
    "trend": 100,
    "volatility": 66.8,
    "news": 96
  },
  "market_data": {
    "rsi14": 68,
    "atr": 4.2,
    "returns": {"return_1d": 0.012, "return_5d": 0.043}
  },
  "news": [
    {
      "headline": "Nvidia raises guidance on AI demand",
      "sentiment": "positive"
    }
  ]
}
```

---

# 🧠 Analysis Logic

The Options Agent uses a strict combination of LLM decision-making and Python mathematical rigor:

## 1. Aggregation
Pulls the latest candidate data from across the pipeline.

## 2. Options Fetching (Alpaca)
Uses the `OptionHistoricalDataClient` to pull the options chain for the underlying symbol.

## 3. Pre-Filtering (Python)
Options chains are massive. To prevent LLM context-window overflow and ensure high-quality trades, Python aggressively filters the chain:
- **Expiration**: Only contracts between 15 and 90 days to expiration.
- **Strike**: Only strikes within ±10% of the current spot price.
- **Liquidity**: Minimum Open Interest ≥ 50, Minimum Volume ≥ 10.
- **Spreads**: Rejects contracts where the Bid/Ask spread is greater than 10% of the mid-price.

## 4. Strategy Generation (LLM)
Passes the aggregated market data and the filtered options chain to Groq (`openai/gpt-oss-120b` / `llama-3.1-70b-versatile`). The LLM is strictly constrained to output one of 6 approved directional strategies: **Long Call, Long Put, Bull Call Spread, Bear Put Spread, Bear Call Spread, or Bull Put Spread**. (Calendar and Diagonal spreads are explicitly banned due to mathematical unpredictability).

## 5. Math & Validation Engine (Python)
LLMs are bad at math and can hallucinate data. The Python engine intercepts the LLM output and:
- **Verifies Existence & Extracts OCC**: Confirms the strikes and expirations selected by the LLM actually exist in the filtered chain, and seamlessly extracts the 21-character OCC Symbol (e.g. `AAPL260915C00180000`) to pass downstream.
- **Enforces Real Prices**: Uses the actual `Ask` price for buy legs and `Bid` price for sell legs (crossing the spread).
- **Calculates PNL**: Mathematically calculates Net Debit/Credit, Max Profit, Max Loss, Breakeven, and Risk/Reward.
- **Rejects Bad Trades**: If the strategy is mathematically impossible or yields a guaranteed loss, it is rejected entirely.

---

# 📤 Output Format

The agent saves its verified proposals in the parent-level `Options Agent Output` directory. 

```json
[
  {
    "symbol": "NVDA",
    "strategy": {
      "type": "BullCallSpread",
      "confidence": 0.89,
      "legs": [
        {
          "action": "BUY",
          "option_type": "CALL",
          "strike": 180.0,
          "expiration": "2026-09-15",
          "price": 3.60
        },
        {
          "action": "SELL",
          "option_type": "CALL",
          "strike": 190.0,
          "expiration": "2026-09-15",
          "price": 1.20
        }
      ],
      "risk_reward": {
        "net_debit": 2.40,
        "max_profit": 7.60,
        "max_loss": 2.40,
        "breakeven": 182.40,
        "risk_reward_ratio": 3.17
      },
      "reason": "Strong bullish momentum, positive news and favorable call option structure."
    }
  }
]
```

---

# 🔗 Integration With Other Agents

The Options Agent does **not** make the final trading decision. It formulates the *optimal way* to trade the asset via options. Its output becomes one input to the Decision Agent, alongside the Market Agent and News Agent.

---

# 🚫 What the Options Agent Does NOT Do

The Options Agent is responsible for **options strategy formulation only**.

It does **not**:

- ❌ Perform core sentiment analysis (That's the News Agent)
- ❌ Provide fundamental stock analysis
- ❌ Make the final `TRADE/PASS` decision (That's the Decision Agent)
- ❌ Execute live trades directly with the broker

---

# 🚀 Quick Start

## 1. Install Dependencies

```bash
pip install -r ../requirements.txt
```

## 2. Configure Environment

Create a `.env` file in the `Options-Agent` folder:

```env
ALPACA_API_KEY=your_alpaca_key
ALPACA_SECRET_KEY=your_alpaca_secret
GROQ_API_KEY=your_groq_key
GROQ_MODEL=openai/gpt-oss-120b
```

## 3. Run the Agent

```bash
python options_agent.py
```

*Note: The script features a graceful fallback. If API keys are missing, it will use mock options data so you can test the entire pipeline locally without crashing.*

---

# 📁 Project Structure

```text
Options-Agent/
│
├── .env
├── options_agent.py
└── readme.optionsagent.md
```

---

# 🛠️ Dependencies

| Package | Purpose |
|---|---|
| `groq` | LLM API client |
| `alpaca-py` | Fetching real-time/historical options chains |
| `python-dotenv` | Environment variable management |
| `pandas` | Underlying data structuring |

---

# 👨‍💻 Team Responsibility

| Component | Developer |
|---|---|
| 🔎 Market Scanner | M-Rohan-Sohail |
| 🤖 Market Agent | Subhan-Developer |
| 📰 News Agent | Team Member |
| 📊 **Options Agent** | **Team Member** |
| 🧠 Decision Agent | Team Member |

---

# 🧠 In Simple Words

The Options Agent is basically a **Quantitative Options Strategist**.

It answers one main question:

> **"Given the current market context and live liquidity, what is the mathematically optimal multi-leg options trade we can execute for this stock right now?"**

---

## 🏆 Project

**Alpaca AI Hackathon 2026**

**Layer:** Agentic Layer  
**Component:** Options Agent  
