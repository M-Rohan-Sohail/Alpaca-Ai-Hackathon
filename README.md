# Architecture Audit: Alpaca AI Trading Agents

This document provides a comprehensive audit of the finalized multi-agent options trading system.

## 1. System Philosophy: "AI Proposes, Math Disposes"
The system strictly decouples **qualitative intelligence** (LLMs) from **quantitative risk management** (Deterministic Python). The LLMs act as a creative advisory board to propose trading strategies, while a rigid Python engine enforces mathematical safety rules and execution mechanics. At no point can an LLM override capital allocation limits or place orders directly.

---

## 2. Core Pipeline Flow
The entire pipeline is orchestrated by `Run_Pipeline.py`, executing locally in batch increments.

> `Data Ingestion (MCP + API) -> Data Processing -> Market Agent -> News Agent -> Options Agent -> Decision Agent -> Risk Engine -> Execution Agent -> Position Monitor -> Trade Journal`

---

## 3. Agent & Component Roles

### 3.1 Data Ingestion (MCP + API)
- **Role**: Fetch raw state from Alpaca and Serper.
- **MCP Integration**: Fully integrates the **Alpaca MCP Server** via a programmatic Python `mcp_client.py`. It securely fetches global account constraints (`get_account_info`) and real-time equity snapshots (`get_stock_snapshot`) using the MCP protocol.
- **API Fallback**: Uses `alpaca-py` exclusively for features not yet fully supported by the MCP server (e.g., 100-day historical OHLCV bars and deep option chain Greeks).
- **Directory**: `Data-Ingestion/`

### 3.2 Data Processing & Deterministic Filter
- **Role**: Computes technical indicators (EMA, RSI, MACD) and filters out assets with unfavorable liquidity, IV, or trend alignment.
- **Directory**: `Data-Processing/`

### 3.3 Market Agent (LLM)
- **Role**: Analyzes the filtered technical OHLCV data to formulate a macro directional bias (e.g., `BULLISH` or `BEARISH`).
- **Model**: Qwen3.8-27b via Groq.
- **Directory**: `Market-Agent/`

### 3.4 News Agent (LLM)
- **Role**: Replaces naive keyword-matching with deep semantic sentiment classification. It analyzes Serper news headlines, outputting a `positive`/`negative`/`neutral` sentiment and a confidence score.
- **Model**: Qwen3.8-27b via Groq.
- **Directory**: `News-Agent/` (Part of Data-Processing flow).

### 3.5 Options Agent (LLM)
- **Role**: Ingests the Market and News biases alongside live Option Chains to construct specific, multi-leg options strategies (e.g., Bull Call Spreads).
- **Output**: OCC Symbols, Strikes, Expirations, and Leg Directions (Buy/Sell).
- **Directory**: `Options-Agent/`

### 3.6 Decision Agent (Qualitative Authority)
- **Role**: The final AI judge. It reviews the outputs from the previous agents, synthesizing the data into a human-readable qualitative rationale, and issues a simple `TRADE` or `PASS` directive.
- **Constraint**: It is explicitly stripped of all sizing and capital allocation authority.
- **Directory**: `Decision-agent/`

### 3.7 Risk Assessment Engine (Quantitative Authority)
- **Role**: The absolute, un-overrideable mathematical gatekeeper. 
- **Mechanism**:
  1. **Economics**: Computes exact Max Loss, Max Profit, and Breakeven for the proposed multi-leg spreads using `shared_portfolio.py`.
  2. **Capacity Check**: Evaluates the trade against `config.json` limits (Account Risk, Daily Loss, Buying Power, Exposure limits).
  3. **Resize & Reject**: Converts available dollar-risk into integer contracts. If limits are breached or the R:R is unacceptable, it issues a `REJECT` directive, logging a `binding_constraint`.
- **Directory**: `Risk Assessment Engine/`

### 3.8 Execution Agent
- **Role**: The exclusive bridge to the Alpaca Paper Trading API.
- **Constraint**: It will **only** execute orders that contain an `ACCEPT` flag from the Risk Engine. It rejects any attempt by the LLM to route trades independently.
- **Outputs**: Generates execution receipts and updates the initial entry state in the Trade Journal.
- **Directory**: `Execution Agent/`

### 3.9 Position Monitor & Exits
- **Role**: Continuously monitors open positions in the Trade Journal against live Alpaca prices.
- **Mechanism**: Strictly deterministic. It evaluates Unrealized P&L against hardcoded constraints in `config.json` (e.g., Take Profit > 50%, Stop Loss < -20%, Max DTE limit).
- **Output**: Generates `exit_orders_[timestamp].json` directives, which the Execution Agent executes to close the trades.
- **Directory**: `Position-Monitor/`

---

## 4. Frontend & UI Strategy
The frontend acts as a **Visualization Layer Only**, consuming the local JSON batch files via a Fast API backend proxy.
- **Transparency**: Clearly visualizes the hand-off between the AI Agents (italicized qualitative text) and the Risk Engine (bold quantitative math).
- **Safety**: Banned from generating Alpaca payloads or overriding the Risk Engine. All manual force-closures must be routed through the backend `POST /api/execute/close` endpoint to prevent rogue client-side execution.
