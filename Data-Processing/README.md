# ⚙️ Data Processing v1

<p align="center">
  <strong>The Technical & Sentiment Calculator for the Alpaca AI Hackathon 2026</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Layer-Data%20Layer-blue" alt="Data Layer">
  <img src="https://img.shields.io/badge/Component-Data%20Processing-purple" alt="Data Processing">
  <img src="https://img.shields.io/badge/Python-3.10%2B-yellow" alt="Python">
</p>

---

## 📌 Overview

The **Data Processing** module acts as the analytical calculator before handing data off to the AI agents.

Its job is to:
> **Take the raw data fetched by Data Ingestion, compute technical indicators (RSI, SMA, ATR) and evaluate news sentiment via a context-aware LLM (Groq/OpenRouter), and package it into a clean "State" JSON for the trading agents.**

---

## 🔄 Flow

```text
 📂 Data-Ingestion (Raw JSON Data)
       ↓
 🔍 data_loader.py (Automatically finds latest raw data)
       ↓
 ⚙️ run_processing.py (Calculates TA & Batched LLM Sentiment)
       ↓
 💾 Data-Processing-Output/DP_RUN_1_<timestamp>/
```

---

# 📥 Input Sources
The `data_loader.py` utility automatically scans the `Data-Ingestion` folder to find the absolute most recent `DI_RUN_1_<timestamp>` folder to use as its input source.

---

# 📤 Output Format
The processor calculates the final AI-ready state and outputs it as clean JSON. Old output folders are automatically deleted to save space.

```json
{
  "symbol": "AAPL",
  "price": 314.58,
  "returns": {
    "return_1d": 0.0036,
    "return_5d": 0.0105,
    "return_20d": -0.0565
  },
  "trend": {
    "sma20": 309.32,
    "sma50": 311.52,
    "rsi14": 52.41
  },
  "volatility": {
    "daily_std": 0.0197,
    "atr": 7.11
  },
  "news": [
    {
      "headline": "Company beats earnings expectations and raises full-year guidance",
      "sentiment": "positive",
      "confidence": 0.95
    }
  ]
}
```

---

# 🚀 Quick Start

Run the processing script from the root workspace directory:
```bash
python Data-Processing/run_processing.py
```
