# 📉 Position Monitor v1

<p align="center">
  <strong>The Deterministic Exit Engine for the Alpaca AI Hackathon 2026</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Layer-Agentic%20Layer-blue" alt="Agentic Layer">
  <img src="https://img.shields.io/badge/Component-Position%20Monitor-purple" alt="Position Monitor">
  <img src="https://img.shields.io/badge/Python-3.10%2B-yellow" alt="Python">
</p>

---

## 📌 Overview

The **Position Monitor** acts as the deterministic watcher for open trades. It is executed before the main ingestion pipeline to ensure that existing positions can be closed to free up capital before new entries are evaluated.

Its job is to:
> **Evaluate all open positions against strict deterministic rules (Stop Loss, Take Profit, Max DTE, Max Holding Days) and trigger automated exit orders via the Execution Agent without any LLM intervention.**

---

## 🔄 Flow

```text
 📂 Alpaca API (Fetches open positions)
       ↓
 📝 Trade Journal (Maps legs to multi-leg strategies & fetches entry data)
       ↓
 ⚙️ run_monitor.py (Evaluates PnL & Time constraints)
       ↓
 💾 SAVE-DATA-PER-AGENT/Position-Monitor-Output/exit_orders_<timestamp>.json
       ↓
 🚀 Execution Agent (Submits SELL/BUY_TO_CLOSE orders)
```

---

# 📥 Evaluation Rules
The monitor loads the centralized configuration from `User_Config/config.json` and evaluates:
1. **Take Profit (%)**: e.g., Close if strategy PnL > 50%.
2. **Stop Loss (%)**: e.g., Close if strategy PnL < -25%.
3. **Max DTE**: e.g., Close if options expire in less than 3 days.
4. **Max Holding Days**: e.g., Close if position held for > 10 days.

---

# 🚫 What the Position Monitor Does NOT Do

- ❌ Talk to Large Language Models (LLMs).
- ❌ Formulate exit strategies dynamically.
- ❌ Make speculative market calls (It only follows strict math constraints).
