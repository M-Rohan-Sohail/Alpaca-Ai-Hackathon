import os
import sys
from dotenv import load_dotenv
import json
import pandas as pd
from datetime import datetime, timezone
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange

# Ensure we can import from User_Config and local data_loader
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT_DIR, '.env'))
sys.path.append(ROOT_DIR)

from User_Config.config import load_config
from data_loader import load_latest_bars, load_latest_news, load_latest_options


def compute_returns(bars: list[dict]) -> dict:
    closes = [b["c"] for b in bars]

    def pct_change(days):
        if len(closes) < days + 1:
            return None
        return float(round((closes[-1] - closes[-1 - days]) / closes[-1 - days], 4))

    return {
        "return_1d": pct_change(1),
        "return_5d": pct_change(5),
        "return_20d": pct_change(20),
    }


def compute_trend(bars: list[dict]) -> dict:
    df = pd.DataFrame(bars)
    closes = df["c"]

    trend = {}
    if len(closes) >= 20:
        trend["sma20"] = float(round(SMAIndicator(closes, window=20).sma_indicator().iloc[-1], 2))
    else:
        trend["sma20"] = None

    if len(closes) >= 50:
        trend["sma50"] = float(round(SMAIndicator(closes, window=50).sma_indicator().iloc[-1], 2))
    else:
        trend["sma50"] = None

    if len(closes) >= 14:
        trend["rsi14"] = float(round(RSIIndicator(closes, window=14).rsi().iloc[-1], 2))
    else:
        trend["rsi14"] = None

    return trend


def compute_volatility(bars: list[dict]) -> dict:
    df = pd.DataFrame(bars)
    closes = df["c"]
    highs = df["h"]
    lows = df["l"]

    # Daily return standard deviation
    daily_returns = closes.pct_change().dropna()
    daily_std = float(round(daily_returns.std(), 4)) if len(daily_returns) > 1 else None

    # ATR
    if len(closes) >= 14:
        atr = AverageTrueRange(high=highs, low=lows, close=closes, window=14)
        atr_value = float(round(atr.average_true_range().iloc[-1], 2))
    else:
        atr_value = None

    return {
        "daily_std": daily_std,
        "atr": atr_value
    }


def compute_volume(bars: list[dict]) -> dict:
    volumes = [b["v"] for b in bars]
    today_volume = int(volumes[-1])
    avg20 = int(sum(volumes[-20:]) / len(volumes[-20:])) if len(volumes) >= 1 else None
    return {
        "today": today_volume,
        "avg20": avg20
    }


def analyze_news_batch(news_items: list[dict]) -> list[dict]:
    if not news_items:
        return []
        
    results = []
    
    # Full-fledged financial keyword dictionary
    positive_words = [
        "beat", "up", "growth", "high", "raise", "strong", "win", "good", "surge", "jump",
        "upgrade", "bullish", "profit", "gain", "dividend", "acquisition", "merger",
        "record", "outperform", "soar", "rally", "success", "approval", "expand",
        "exceed", "revenue", "partnership", "breakthrough", "launch", "demand", "rebound"
    ]
    
    negative_words = [
        "miss", "down", "low", "cut", "weak", "lose", "bad", "lawsuit", "investigation",
        "drop", "fall", "downgrade", "bearish", "loss", "decline", "warning", "bankrupt",
        "fraud", "underperform", "plunge", "crash", "fail", "rejection", "shrink",
        "shortfall", "layoff", "penalty", "scandal", "selloff", "probe", "debt", "recession"
    ]
    
    for item in news_items:
        title = item.get("title", "").lower()
        
        # Calculate raw hits
        pos_count = sum(1 for w in positive_words if w in title.split())
        neg_count = sum(1 for w in negative_words if w in title.split())
        
        # Also check for substrings for certain dynamic words
        pos_count += sum(1 for w in ["soar", "jump", "rally", "gain", "beat"] if w in title and w not in title.split())
        neg_count += sum(1 for w in ["plunge", "crash", "drop", "fall", "miss"] if w in title and w not in title.split())
        
        if pos_count > neg_count:
            sentiment = "positive"
        elif neg_count > pos_count:
            sentiment = "negative"
        else:
            sentiment = "neutral"
            
        results.append({
            "headline": item.get("title", ""),
            "sentiment": sentiment,
            "confidence": 0.5
        })
        
    return results


def process_news(news_items: list[dict]) -> list[dict]:
    return analyze_news_batch(news_items)


def process_options(options_raw: list[dict], max_contracts: int = 5) -> list[dict]:
    simplified = []
    for opt in options_raw[:max_contracts]:
        simplified.append({
            "strike": opt.get("strike"),
            "exp": opt.get("exp"),
            "bid": opt.get("bid"),
            "ask": opt.get("ask"),
            "iv": opt.get("iv"),
            "delta": opt.get("delta"),
        })
    return simplified


def build_structured_state(symbol: str) -> dict:
    bars = load_latest_bars(symbol)
    news = load_latest_news(symbol)

    try:
        options_raw = load_latest_options(symbol)
    except FileNotFoundError:
        options_raw = []

    state = {
        "symbol": symbol,
        "price": float(bars[-1]["c"]),
        "returns": compute_returns(bars),
        "trend": compute_trend(bars),
        "volatility": compute_volatility(bars),
        "volume": compute_volume(bars),
        "options": process_options(options_raw),
        "news": process_news(news)
    }
    return state


def get_run_folder_name(base_folder: str, timestamp: str) -> str:
    """
    Deletes previous DP_RUN folders and returns the new folder name.
    """
    import shutil
    os.makedirs(base_folder, exist_ok=True)
    existing_runs = [d for d in os.listdir(base_folder) if d.startswith("DP_RUN_") and os.path.isdir(os.path.join(base_folder, d))]
    
    for d in existing_runs:
        shutil.rmtree(os.path.join(base_folder, d))
            
    return f"DP_RUN_1_{timestamp}"


def save_state(state: dict, run_folder: str):
    os.makedirs(run_folder, exist_ok=True)
    filename = f"{state['symbol']}_state.json"
    filepath = os.path.join(run_folder, filename)
    with open(filepath, "w") as f:
        json.dump(state, f, indent=2)
    print(f"Saved: {filepath}")


if __name__ == "__main__":
    config_path = os.path.join(ROOT_DIR, "User_Config", "config.json")
    print("Loading and verifying User Config...")
    config = load_config(config_path)
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    output_base_dir = os.path.join(ROOT_DIR, "SAVE-DATA-PER-AGENT", "Data-Processing-Output")
    run_folder_name = get_run_folder_name(output_base_dir, timestamp)
    run_folder_path = os.path.join(output_base_dir, run_folder_name)
    
    print(f"Saving processing output to: {run_folder_path}")

    for symbol in config.assets:
        print(f"\nProcessing {symbol}...")
        try:
            state = build_structured_state(symbol)
            save_state(state, run_folder_path)
        except Exception as e:
            print(f"Error processing {symbol}: {e}")

    print("\nDone processing all symbols.")
