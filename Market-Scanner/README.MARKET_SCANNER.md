# 🔎 Market Scanner

<p align="center">
  <strong>Autonomous asset evaluation and ranking for the Alpaca AI Hackathon 2026</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Layer-Data%20Layer-blue" alt="Data Layer">
  <img src="https://img.shields.io/badge/Component-Market%20Scanner-teal" alt="Market Scanner">
  <img src="https://img.shields.io/badge/Python-3.10%2B-yellow" alt="Python">
  <img src="https://img.shields.io/badge/Status-Active-success" alt="Status">
</p>

---

## 📌 Overview

The **Market Scanner** is an autonomous component that acts as the gateway to the AI system.

Its job is simple:

> **Evaluate and rank a large pool of financial assets based on quantitative metrics and select the top candidates with the highest "Opportunity Score".**

The scanner filters out the noise and ensures that the downstream AI Decision Agents (Market, News, Options) only spend their compute cycles analyzing the most promising stocks.

- 📈 Momentum & Trend evaluation
- 📦 Volume & Volatility analysis
- 🏆 Final Opportunity Score ranking

The result is saved to disk to be picked up by the Agentic Layer.

---

## 🔄 Agentic Layer Flow

```text
                      📊 RAW MARKET DATA
                                │
                                ▼
                    ┌───────────────────────┐
                    │  🔎 MARKET SCANNER    │
                    │   Ranks Candidates    │
                    └───────────┬───────────┘
                                │
                          Top Candidates
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
                 └───────────┼───────────────┘
                             │
                       ┌─────┴─────┐
                       ▼           ▼
                     TRADE        PASS
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

# 🎯 What Does the Market Scanner Do?

The Market Scanner receives a raw dump of market metrics for hundreds of assets.

It looks at:

```text
💰 Price & Returns
📈 SMA20 & SMA50
📊 RSI14
📉 Volatility (ATR, Std)
📦 Volume surges
```

Then it produces a normalized 0-100 score for:

```text
              RAW ASSET POOL
                     │
                     ▼
              🔎 MARKET SCANNER
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
     Momentum      Trend       Volatility
        │            │            │
        └────────────┼────────────┘
                     ▼
             Opportunity Score
```

---

# 📥 Input Format

The scanner takes a JSON list of assets containing their metrics.

```json
{
  "symbol": "NVDA",
  "price": 180.45,
  "returns": {
    "return_1d": 0.012,
    "return_5d": 0.043,
    "return_20d": 0.087
  },
  "trend": {
    "sma20": 178.2,
    "sma50": 173.5,
    "rsi14": 68
  },
  "volatility": {
    "daily_std": 0.018,
    "atr": 4.2
  },
  "volume": {
    "today": 34000000,
    "avg20": 25000000
  }
}
```

---

# 🧠 Analysis Logic

All individual component scores are strictly clamped between `0.0` and `100.0`.

1. **Momentum Score (30%)**: Normalized 5-day return divided by daily standard deviation.
2. **Trend Score (30%)**: 25 points each for `price > SMA20`, `price > SMA50`, `SMA20 > SMA50`, and `RSI14 > 60`.
3. **Volume Score (15%)**: Measures the surge in volume against the 20-day average.
4. **Volatility Score (15%)**: Evaluates the ATR percentage to find the "sweet spot" for options trading.
5. **News Score (10%)**: A preliminary baseline sentiment score.

---

# 📤 Output Format

The `market_scanner.py` script returns a JSON payload containing the candidates and their sub-metrics. It outputs directly to the parent-level `Market Scanner Output` directory.

```json
{
  "candidates": [
    {
      "symbol": "NVDA",
      "price": 180.45,
      "trend": {
        "sma20": 178.2,
        "sma50": 173.5,
        "rsi14": 68
      },
      "volatility": {
        "daily_std": 0.018,
        "atr": 4.2
      },
      "volume": {
        "today": 34000000,
        "avg20": 25000000
      }
    }
  ],
  "run_timestamp": "20260825_210322"
}
```

---

# 🔗 Integration With Other Agents

The Market Scanner is the **first step** in the pipeline. It does not perform deep analysis or LLM generation. Instead, its output JSON is read dynamically by the Market Agent and News Agent.

---

# 🚫 What the Market Scanner Does NOT Do

The Market Scanner is responsible for **filtering and ranking only**.

It does **not**:

- ❌ Perform qualitative LLM analysis
- ❌ Execute buy/sell orders
- ❌ Scrape live web data
- ❌ Make the final `TRADE/PASS` decision

---

# 🚀 Quick Start

## 1. Run the Scanner

```bash
python market_scanner.py
```

*Note: The script currently uses a dummy asset pool for testing.*

---

# 📁 Project Structure

```text
Market-Scanner/
│
├── market_scanner.py
└── README.MARKET_SCANNER.md
```

---

# 🛠️ Dependencies

The Market Scanner relies purely on Python's built-in standard libraries.

- `json`
- `os`
- `datetime`

No external `pip` packages required!

---

# 👨‍💻 Team Responsibility

| Component | Developer |
|---|---|
| 🔎 **Market Scanner** | **M-Rohan-Sohail** |
| 🤖 Market Agent | Subhan-Developer |
| 📰 News Agent | Team Member |
| 📊 Options Agent | Team Member |
| 🧠 Decision Agent | Team Member |

---

# 🧠 In Simple Words

The Market Scanner is basically a **Talent Scout**.

It looks at hundreds of stocks and answers one main question:

> **"Which of these stocks are moving enough right now to be worth our AI agents' time?"**

---

## 🏆 Project

**Alpaca AI Hackathon 2026**

**Layer:** Data Layer  
**Component:** Market Scanner  
**Developer:** M-Rohan-Sohail
