# 🛠️ User Config v1

<p align="center">
  <strong>The Rules Engine for the Alpaca AI Hackathon 2026</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Layer-Config%20Layer-blue" alt="Config Layer">
  <img src="https://img.shields.io/badge/Component-User%20Config-purple" alt="User Config">
  <img src="https://img.shields.io/badge/Python-3.10%2B-yellow" alt="Python">
</p>

---

## 📌 Overview

The **User Config** module is the central source of truth for the entire trading bot's parameters.

Its job is to:
> **Define the trading universe (assets) and enforce strict risk management rules using Pydantic validation.**

---

## 🔄 Flow

```text
 📝 config.json (Human-readable rules)
       ↓
 🛡️ config.py (Pydantic Validator)
       ├─► 📥 Data Ingestion (Knows what to fetch)
       └─► ⚙️ Data Processing (Knows what to process)
```

---

# 📥 Input Sources
A simple `config.json` file where the user defines their acceptable risk and asset targets.

```json
{
  "assets": [
    "SPY", "QQQ", "IWM", "DIA", "NVDA", "AAPL"
  ],
  "max_risk_per_trade_pct": 1.0,
  "max_daily_loss_pct": 3.0,
  "max_open_positions": 5,
  "max_exposure_pct": 20.0,
  "min_risk_reward": 1.5,
  "max_holding_days": 10,
  "allowed_strategies": ["BullCallSpread", "LongCall"]
}
```

---

# 📤 Output Format
The `config.py` script exports a `load_config()` function that parses the JSON into a strongly-typed `UserConfig` Python object. If any rule is violated (e.g., an empty asset list, or a risk percentage over 100), it throws a hard error before the bot can even start.

---

# 🧠 In Simple Words
This is the "steering wheel" of the bot. You edit `config.json` to tell the bot exactly what to trade and how much money it is allowed to risk. 
