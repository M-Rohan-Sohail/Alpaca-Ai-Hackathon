# 🤖 Market Agent v1

<p align="center">
  <strong>AI-powered technical market analysis for the Alpaca AI Hackathon 2026</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Layer-Agentic%20Layer-blue" alt="Agentic Layer">
  <img src="https://img.shields.io/badge/Component-Market%20Agent-purple" alt="Market Agent">
  <img src="https://img.shields.io/badge/Python-3.10%2B-yellow" alt="Python">
  <img src="https://img.shields.io/badge/Status-Active-success" alt="Status">
</p>

---

## 📌 Overview

The **Market Agent** is an AI-powered component of the **Agentic Layer**.

Its job is simple:

> **Analyze a stock's technical market data and determine whether the current market trend is BULLISH, BEARISH, or NEUTRAL.**

The agent combines technical indicators such as price, moving averages, RSI, volatility, and volume to produce a structured market analysis with:

- 📈 Market direction
- 🎯 Confidence score
- 🧠 Reasoning
- 🔑 Key factors

The result is then passed to the **Decision Agent**, where it is combined with the outputs from the News Agent and Options Agent.

---

## 🔄 Agentic Layer Flow

```text
                         🔎 MARKET SCANNER
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

# 🎯 What Does the Market Agent Do?

The Market Agent receives structured market data for a selected stock.

It looks at:

```text
💰 Price
📈 SMA20
📈 SMA50
📊 RSI
📉 Volatility
📏 ATR
📦 Volume
```

Then it produces:

```text
                  MARKET DATA
                       │
                       ▼
                🤖 MARKET AGENT
                       │
              Technical Analysis
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       🟢 BULLISH   ⚪ NEUTRAL   🔴 BEARISH
          │            │            │
          └────────────┼────────────┘
                       ▼
               Confidence + Reasoning
```

---

# 📥 Input Format

The Market Agent expects a structured market-data object.

```json
{
  "symbol": "NVDA",
  "price": 180.45,
  "trend": {
    "sma20": 178.20,
    "sma50": 173.50,
    "rsi14": 68.0
  },
  "volatility": {
    "daily_std": 0.018,
    "atr": 4.20
  },
  "volume": {
    "today": 34000000,
    "avg20": 25000000
  }
}
```

### Input Fields

| Field | Type | Description |
|---|---|---|
| `symbol` | `string` | Stock ticker symbol |
| `price` | `float` | Current market price |
| `trend.sma20` | `float` | 20-day Simple Moving Average |
| `trend.sma50` | `float` | 50-day Simple Moving Average |
| `trend.rsi14` | `float` | 14-day Relative Strength Index |
| `volatility.daily_std` | `float` | Daily price standard deviation |
| `volatility.atr` | `float` | Average True Range |
| `volume.today` | `int` | Current trading volume |
| `volume.avg20` | `int` | 20-day average volume |

---

# 🧠 Analysis Logic

The Market Agent evaluates the relationship between price and technical indicators.

## 🟢 Bullish

A strong bullish setup occurs when:

```text
Price > SMA20 > SMA50
AND
RSI > 60
```

Example:

```text
Price = $180.45
SMA20  = $178.20
SMA50  = $173.50
RSI    = 68
```

### Result

```text
🟢 BULLISH
```

The stock is showing a strong positive technical trend.

---

## 🔴 Bearish

A strong bearish setup occurs when:

```text
Price < SMA20 < SMA50
AND
RSI < 40
```

Example:

```text
Price = $150
SMA20  = $160
SMA50  = $165
RSI    = 32
```

### Result

```text
🔴 BEARISH
```

The stock is showing a negative technical trend.

---

## ⚪ Neutral

When the indicators provide mixed signals:

```text
⚪ NEUTRAL
```

Example:

```text
Price = $175
SMA20  = $174
SMA50  = $176
RSI    = 52
```

There is no strong bullish or bearish signal.

> **Note:** These conditions guide the analysis. The agent considers the available market information together when generating its final assessment.

---

# 📤 Output Format

The `analyze()` function returns a structured JSON object.

```json
{
  "symbol": "NVDA",
  "direction": "BULLISH",
  "confidence": 0.85,
  "reasoning": "Price is above both moving averages and RSI indicates strong positive momentum.",
  "key_factors": [
    "Price > SMA20 > SMA50",
    "RSI indicates bullish momentum",
    "Positive price trend"
  ],
  "timestamp": "2026-08-25T17:05:00",
  "model_used": "gpt-4"
}
```

### Output Fields

| Field | Type | Description |
|---|---|---|
| `symbol` | `string` | Stock that was analyzed |
| `direction` | `string` | `BULLISH`, `BEARISH`, or `NEUTRAL` |
| `confidence` | `float` | Confidence score from `0.0` to `1.0` |
| `reasoning` | `string` | Explanation of the analysis |
| `key_factors` | `array` | Main factors behind the result |
| `timestamp` | `string` | Analysis timestamp |
| `model_used` | `string` | LLM model used |

---

# 🔗 Integration With Other Agents

The Market Agent does **not** make the final trading decision.

Instead, its output becomes one input to the Decision Agent.

### Example

```text
🤖 Market Agent
       │
       ├── Direction: BULLISH
       ├── Confidence: 85%
       └── Key Factors
              │
              ▼
       📰 News Agent
              │
              ├── Sentiment: POSITIVE
              │
              ▼
       📊 Options Agent
              │
              ├── Strategy: Bull Call Spread
              │
              ▼
       🧠 Decision Agent
              │
         ┌────┴────┐
         ▼         ▼
      🟢 TRADE   ⚪ PASS
```

---

# 🚫 What the Market Agent Does NOT Do

The Market Agent is responsible for **market analysis only**.

It does **not**:

- ❌ Execute buy orders
- ❌ Execute sell orders
- ❌ Decide position size
- ❌ Perform final risk checks
- ❌ Make the final `TRADE/PASS` decision

Those responsibilities belong to other components of the system.

---

# 🚀 Quick Start

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

## 2. Configure Environment

Create a `.env` file:

```env
OPENAI_API_KEY=your-api-key
```

## 3. Import the Agent

```python
from agentic_layer.market_agent import MarketAgent
```

## 4. Initialize

### Sandbox Mode

Use sandbox mode for testing without making an LLM API request:

```python
agent = MarketAgent(sandbox_mode=True)
```

### Live Mode

Use live mode for actual LLM analysis:

```python
agent = MarketAgent(
    model="gpt-4",
    temperature=0.3,
    sandbox_mode=False
)
```

## 5. Prepare Market Data

```python
market_data = {
    "symbol": "NVDA",
    "price": 180.45,
    "trend": {
        "sma20": 178.20,
        "sma50": 173.50,
        "rsi14": 68.0
    },
    "volatility": {
        "daily_std": 0.018,
        "atr": 4.20
    },
    "volume": {
        "today": 34000000,
        "avg20": 25000000
    }
}
```

## 6. Run the Analysis

```python
result = agent.analyze(market_data)

print(result["direction"])
print(result["confidence"])
print(result["reasoning"])
```

### Example

```text
BULLISH
0.85
Price is above both moving averages and RSI indicates strong positive momentum.
```

---

# 🧪 Testing

Run the test suite:

```bash
python -m pytest tests/test_market_agent.py -v
```

### Test Scenarios

| Scenario | Expected |
|---|---|
| Strong bullish trend | 🟢 `BULLISH` |
| Strong bearish trend | 🔴 `BEARISH` |
| Mixed signals | ⚪ `NEUTRAL` |
| Overbought bullish trend | 🟢 `BULLISH` |
| Oversold bearish trend | 🔴 `BEARISH` |

---

# 💻 Standalone Usage

Run the Market Agent directly:

```bash
python3 market_agent.py
```

Example output:

```text
🚀 Market Agent - Alpaca AI Hackathon 2026
==================================================

📈 Analysis Results:

Symbol: NVDA
Direction: BULLISH
Confidence: 85.00%

Reasoning:
Price is above both moving averages and RSI indicates strong positive momentum.

Key Factors:
- Price > SMA20 > SMA50
- RSI indicates bullish momentum
- Positive price trend
```

---

# 📁 Project Structure

```text
agentic_layer/
│
├── __init__.py
├── market_agent.py
├── requirements.txt
├── tests/
│   └── test_market_agent.py
└── README.MARKET_AGENT.md
```

---

# 🔌 Integration Contract

### Input

```text
Market Scanner
      │
      ▼
Structured Market Data
      │
      ▼
Market Agent
```

### Output

```text
Market Agent
      │
      ▼
Market Analysis
      │
      ▼
Decision Agent
```

The main fields used by downstream agents are:

```python
{
    "symbol": "...",
    "direction": "BULLISH",
    "confidence": 0.85,
    "reasoning": "...",
    "key_factors": [...]
}
```

---

# 🛠️ Dependencies

| Package | Purpose |
|---|---|
| `openai` | LLM API client |
| `python-dotenv` | Environment variable management |

Install:

```bash
pip install -r requirements.txt
```

---

# 👨‍💻 Team Responsibility

| Component | Developer |
|---|---|
| 🔎 Market Scanner | M-Rohan-Sohail |
| 🤖 **Market Agent** | **Subhan-Developer** |
| 📰 News Agent | Team Member |
| 📊 Options Agent | Team Member |
| 🧠 Decision Agent | Team Member |

---

# 🧠 In Simple Words

The Market Agent is basically an **AI technical analyst**.

It answers one main question:

> **"Based on the current market data, does this stock look Bullish, Bearish, or Neutral?"**

```text
📊 Market Data
      ↓
🤖 Market Agent
      ↓
🧠 Technical Analysis
      ↓
┌──────────┬──────────┬──────────┐
│ 🟢       │ ⚪       │ 🔴       │
│ BULLISH  │ NEUTRAL  │ BEARISH  │
└──────────┴──────────┴──────────┘
      ↓
🎯 Confidence + Reasoning
      ↓
🧠 Decision Agent
```

---

## 🏆 Project

**Alpaca AI Hackathon 2026**

**Layer:** Agentic Layer  
**Component:** Market Agent  
**Developer:** Subhan-Developer

---
