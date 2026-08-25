# Market Scanner

The Market Scanner is an autonomous agentic component that evaluates and ranks a list of financial assets (stocks/options) based on a combination of quantitative metrics and news sentiment. It is designed to quickly filter down a large pool of assets into the top candidates with the highest "Opportunity Score" before passing them to the AI Decision Agents.

## Overview

The scanner takes a JSON list of assets containing their current price, volume, volatility, trend indicators, returns, options data, and news sentiment. It processes each asset and assigns individual scores for momentum, trend, volume, volatility, and news, strictly clamped between `0` and `100`. Finally, it calculates a weighted **Opportunity Score** and ranks the candidates.

## Input Format

The script expects a list of dictionaries with the following schema:

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
  },
  "options": [
    {
      "strike": 180,
      "exp": "2026-09-15",
      "bid": 3.5,
      "ask": 3.6,
      "iv": 0.24,
      "delta": 0.55
    }
  ],
  "news": [
    {
      "headline": "Nvidia raises guidance on AI demand",
      "sentiment": "positive",
      "confidence": 0.92
    }
  ]
}
```

## Scoring Logic

All individual component scores are strictly clamped between `0.0` and `100.0`. 

1. **Momentum Score**: Based on `return_5d` / `daily_std`. Normalized across the entire batch (0 to 100 based on min/max of the pool). Defaults to 50 if all assets have the same momentum.
2. **Trend Score**: Calculated by giving 25 points for each of the following bullish conditions: `price > SMA20`, `price > SMA50`, `SMA20 > SMA50`, and `RSI14 > 60`.
3. **Volume Score**: Measures the surge in volume. `min((today / avg20) / 1.5, 1) * 100`.
4. **Volatility Score**: Based on the ATR percentage (`ATR / price * 100`). Higher volatility scores mean the asset is in a "sweet spot" (not too volatile, not too flat). 
5. **News Score**: Analyzes sentiment (`positive=+1`, `neutral=0`, `negative=-1`) multiplied by confidence. If multiple news articles exist, the scores are averaged. Defaults to 50 if no news is present.

### Opportunity Score

The final opportunity score is a weighted sum:
* 30% Momentum
* 30% Trend
* 15% Volume
* 15% Volatility
* 10% News

## Output Format

The `process_market_data` function returns two JSON outputs:
1. **Detailed Score (Output 1)**: Includes the breakdown of individual component scores.
2. **Overall Ranking (Output 2)**: Only includes the final opportunity score and rank, sorted highest to lowest.

## How to Run

To run the scanner with the dummy asset pool:

```bash
python3 market_scanner.py
```
