import json
import os
from datetime import datetime

def clamp(value):
    """Clamps a value between 0 and 100."""
    return max(0.0, min(100.0, float(value)))

def process_market_data(assets, save_output=True):
    """
    Processes a list of asset data dictionaries and returns the ranked candidates.
    """
    if not assets:
        return {"candidates": []}, {"candidates": []}

    # First pass: calculate raw momentum for all assets to find min/max for normalization
    for asset in assets:
        ret_5d = asset.get("returns", {}).get("return_5d", 0)
        daily_std = asset.get("volatility", {}).get("daily_std", 1)  # avoid div by zero if missing
        if daily_std == 0:
            daily_std = 1e-9
        asset["_momentum_raw"] = ret_5d / daily_std

    momentum_raws = [a["_momentum_raw"] for a in assets]
    min_momentum = min(momentum_raws)
    max_momentum = max(momentum_raws)

    scored_candidates = []

    for asset in assets:
        symbol = asset.get("symbol", "UNKNOWN")
        price = asset.get("price", 0)

        # 1. Momentum Score
        raw_mom = asset["_momentum_raw"]
        if max_momentum == min_momentum:
            momentum_score = 50.0
        else:
            momentum_score = 100 * (raw_mom - min_momentum) / (max_momentum - min_momentum)
        momentum_score = clamp(momentum_score)

        # 2. Trend Score
        trend_data = asset.get("trend", {})
        sma20 = trend_data.get("sma20", 0)
        sma50 = trend_data.get("sma50", 0)
        rsi14 = trend_data.get("rsi14", 0)
        
        c1 = 1 if price > sma20 else 0
        c2 = 1 if price > sma50 else 0
        c3 = 1 if sma20 > sma50 else 0
        c4 = 1 if rsi14 > 60 else 0
        trend_score = clamp(((c1 + c2 + c3 + c4) / 4.0) * 100)

        # 3. Volume Score
        volume_data = asset.get("volume", {})
        today_vol = volume_data.get("today", 0)
        avg20_vol = volume_data.get("avg20", 1) # avoid zero division
        if avg20_vol == 0:
            avg20_vol = 1e-9
        volume_ratio = today_vol / avg20_vol
        volume_score = clamp(min(volume_ratio / 1.5, 1.0) * 100)

        # 4. Volatility Score
        atr = asset.get("volatility", {}).get("atr", 0)
        if price > 0:
            atr_pct = (atr / price) * 100
        else:
            atr_pct = 1.0 # arbitrary fallback if no price
        vol_score_raw = 100 - (((atr_pct - 1) / (5 - 1)) * 100)
        volatility_score = clamp(vol_score_raw)

        # 5. News Score
        news_list = asset.get("news", [])
        if not news_list:
            news_score = 50.0
        else:
            news_scores = []
            for item in news_list:
                sentiment = item.get("sentiment", "neutral").lower()
                conf = item.get("confidence", 0.0)
                if sentiment == "positive":
                    val = 1
                elif sentiment == "negative":
                    val = -1
                else:
                    val = 0
                item_score = 50 + (val * conf * 50)
                news_scores.append(item_score)
            news_score = clamp(sum(news_scores) / len(news_scores))

        # 7. Opportunity Score
        opportunity_score = (
            0.30 * momentum_score +
            0.30 * trend_score +
            0.15 * volume_score +
            0.15 * volatility_score +
            0.10 * news_score
        )
        # We don't clamp the weighted sum if the components are already clamped [0, 100] and weights sum to 1.
        # But we can round it.
        opportunity_score = round(opportunity_score, 1)

        scored_candidates.append({
            "symbol": symbol,
            "price": price,
            "trend": trend_data,
            "volatility": asset.get("volatility", {}),
            "volume": volume_data,
            "opportunity_score": opportunity_score,
            "scores": {
                "momentum": round(momentum_score, 1),
                "trend": round(trend_score, 1),
                "volume": round(volume_score, 1),
                "volatility": round(volatility_score, 1),
                "news": round(news_score, 1)
            }
        })

    # Sort by opportunity score descending
    scored_candidates.sort(key=lambda x: x["opportunity_score"], reverse=True)

    # Build Output 1 (Detailed)
    output1 = {"candidates": []}
    # Build Output 2 (Simple)
    output2 = {"candidates": []}

    for rank, candidate in enumerate(scored_candidates, start=1):
        # Detailed entry
        detailed_entry = {
            "rank": rank,
            "symbol": candidate["symbol"],
            "opportunity_score": candidate["opportunity_score"],
            "scores": candidate["scores"]
        }
        output1["candidates"].append(detailed_entry)
        
        # Simple entry (MarketAgent expected input)
        simple_entry = {
            "symbol": candidate["symbol"],
            "price": candidate["price"],
            "trend": candidate["trend"],
            "volatility": candidate["volatility"],
            "volume": candidate["volume"]
        }
        output2["candidates"].append(simple_entry)

    if save_output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(base_dir, "..", "Market Scanner Output")
        os.makedirs(output_dir, exist_ok=True)
        
        # Add marker to identify the latest run output
        output1["run_timestamp"] = timestamp
        output2["run_timestamp"] = timestamp
        
        filename = os.path.join(output_dir, f"market_scan_{timestamp}.json")
        combined_output = {
            "detailed_scores": output1,
            "overall_ranking": output2
        }
        with open(filename, 'w') as f:
            json.dump(combined_output, f, indent=2)

    return output1, output2


# Dummy Input Asset Pool
dummy_input = [
    {
        "symbol": "NVDA",
        "price": 180.45,
        "returns": {"return_1d": 0.012, "return_5d": 0.043, "return_20d": 0.087},
        "trend": {"sma20": 178.2, "sma50": 173.5, "rsi14": 68},
        "volatility": {"daily_std": 0.018, "atr": 4.2},
        "volume": {"today": 34000000, "avg20": 25000000},
        "options": [{"strike": 180, "exp": "2026-09-15", "bid": 3.5, "ask": 3.6, "iv": 0.24, "delta": 0.55}],
        "news": [{"headline": "Nvidia raises guidance on AI demand", "sentiment": "positive", "confidence": 0.92}]
    },
    {
        "symbol": "AAPL",
        "price": 175.50,
        "returns": {"return_1d": -0.002, "return_5d": 0.015, "return_20d": 0.030},
        "trend": {"sma20": 176.0, "sma50": 172.0, "rsi14": 55},
        "volatility": {"daily_std": 0.012, "atr": 3.1},
        "volume": {"today": 45000000, "avg20": 50000000},
        "options": [],
        "news": [{"headline": "Apple announces new features", "sentiment": "positive", "confidence": 0.70}]
    },
    {
        "symbol": "MSFT",
        "price": 330.10,
        "returns": {"return_1d": 0.005, "return_5d": -0.010, "return_20d": 0.025},
        "trend": {"sma20": 335.0, "sma50": 320.0, "rsi14": 45},
        "volatility": {"daily_std": 0.015, "atr": 5.5},
        "volume": {"today": 20000000, "avg20": 22000000},
        "options": [],
        "news": [
            {"headline": "Microsoft faces new regulatory scrutiny", "sentiment": "negative", "confidence": 0.85},
            {"headline": "Cloud revenue grows", "sentiment": "positive", "confidence": 0.90}
        ]
    }
]

if __name__ == "__main__":
    out1, out2 = process_market_data(dummy_input)

    print("=== OUTPUT 1: Detailed Scores ===")
    print(json.dumps(out1, indent=2))
    
    print("\n=== OUTPUT 2: Overall Ranking ===")
    print(json.dumps(out2, indent=2))
