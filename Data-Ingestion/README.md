# 📥 Data Ingestion v1

<p align="center">
  <strong>The Live Market Data Fetcher for the Alpaca AI Hackathon 2026</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Layer-Data%20Layer-blue" alt="Data Layer">
  <img src="https://img.shields.io/badge/Component-Data%20Ingestion-purple" alt="Data Ingestion">
  <img src="https://img.shields.io/badge/Python-3.10%2B-yellow" alt="Python">
</p>

---

## 📌 Overview

The **Data Ingestion** module is the starting point of the trading pipeline. 

Its job is simple:
> **Connect to live APIs (Alpaca & Serper), fetch raw market bars, options chains, and news headlines for the configured assets, and save them locally for downstream processing.**

---

## 🔄 Flow

```text
 ⚙️ User Config (config.json)
       ↓
 📥 run_ingestion.py
       ├─► 📈 Alpaca API (Price Bars & Options)
       └─► 📰 Serper API (News Headlines)
       ↓
 💾 Data-Ingestion/DI_RUN_1_<timestamp>/
```

---

# 📥 Input Sources
- **`User_Config/config.json`**: Dictates exactly which stock symbols to fetch data for.
- **Alpaca API**: Live market data and options.
- **Serper API**: Live Google news data.

---

# 📤 Output Format
When run, the script automatically deletes any old data and creates a fresh run folder containing the newly fetched raw data:

```text
Data-Ingestion/DI_RUN_1_20260828_103224/
 ├── bars/
 │    └── AAPL_bars.json
 ├── news/
 │    └── AAPL_news.json
 └── options/
      └── AAPL_options.json
```

---

# 🚀 Quick Start

Run the ingestion script from the root workspace directory:
```bash
python Data-Ingestion/run_ingestion.py
```
