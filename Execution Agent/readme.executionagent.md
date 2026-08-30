# 🚀 Execution Agent v1

<p align="center">
  <strong>The Final Order Submitter for the Alpaca AI Hackathon 2026</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Layer-Agentic%20Layer-blue" alt="Agentic Layer">
  <img src="https://img.shields.io/badge/Component-Execution%20Agent-purple" alt="Execution Agent">
  <img src="https://img.shields.io/badge/Python-3.10%2B-yellow" alt="Python">
  <img src="https://img.shields.io/badge/Status-Active-success" alt="Status">
</p>

---

## 📌 Overview

The **Execution Agent** is the final component of the **Agentic Layer**.

Its job is simple but critical:

> **Read mathematically validated entry orders from the Risk Assessment Engine (and deterministic exit orders from the Position Monitor), construct exact Alpaca `MarketOrderRequest` or `LimitOrderRequest` payloads, submit live paper trades to the exchange, and strictly sync all executed trades into the Trade Journal.**

The engine bypasses all LLMs. It relies entirely on the precise payloads, extracts OCC Symbols, submits the complex multi-leg combinations via the Alpaca SDK, and then records successful fills into `SAVE-DATA-PER-AGENT/Trade-Journal/`.

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
| 📊 **Options Agent** | Analyzes options strategies & extracts OCC symbols |
| 🧠 **Decision Agent** | Combines outputs to formulate a trading plan |
| 🛡️ **Risk Engine** | Validates trade against portfolio risk rules |
| 🚀 **Execution Agent** | **Executes the live trade on Alpaca** |

---

# 🚀 Quick Start

## 1. Install Dependencies

```bash
pip install -r ../requirements.txt
```

## 2. Configure Environment

The project relies on a shared `.env` file situated at the root directory of the repository (`../.env`).

```env
ALPACA_API_KEY=your_alpaca_key
ALPACA_SECRET_KEY=your_alpaca_secret
```

## 3. Run the Agent

```bash
python execution_agent.py
```

---

# 📁 Project Structure

```text
Execution Agent/
│
├── execution_agent.py
└── readme.executionagent.md
```

---

# 👨‍💻 Team Responsibility

| Component | Developer |
|---|---|
| 🔎 Deterministic Filter | M-Rohan-Sohail |
| 🤖 Market Agent | Subhan-Developer |
| 📰 News Agent | Team Member |
| 📊 Options Agent | Team Member |
| 🧠 Decision Agent | Team Member |
| 🛡️ Risk Engine | Team Member |
| 🚀 **Execution Agent** | **Team Member** |

---

## 🏆 Project

**Alpaca AI Hackathon 2026**

**Layer:** Agentic Layer  
**Component:** Execution Agent
