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
        
    client = None
    try:
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            from groq import Groq
            client = Groq(api_key=api_key)
    except Exception as e:
        print(f"Error initializing Groq client: {e}")
        
    model = os.getenv("NEWS_SENTIMENT_MODEL", "qwen/qwen3.8-27b")
    
    # Process in batches of 10 to avoid huge prompts
    batch_size = 10
    results = []
    
    for i in range(0, len(news_items), batch_size):
        batch = news_items[i:i+batch_size]
        
        # Prepare input with IDs
        prompt_items = []
        for idx, item in enumerate(batch):
            prompt_items.append({
                "id": idx,
                "headline": item.get("title", "")
            })
            
        default_fallback = [{"id": idx, "sentiment": "neutral", "confidence": 0.0} for idx in range(len(batch))]
            
        if not client:
            batch_results = default_fallback
        else:
            prompt = f"""
You are a financial news sentiment classifier.

Your task is to classify the likely financial/market sentiment of each news article
toward the underlying company's stock or financial outlook.

IMPORTANT RULES:
1. Evaluate the COMPLETE financial context of the headline.
2. Do NOT classify based on individual positive/negative words.
3. Consider earnings, revenue, guidance, growth, acquisitions, partnerships,
   regulatory actions, lawsuits, analyst actions, layoffs, product developments,
   macroeconomic effects, and other material financial implications.
4. When positive and negative information conflict, determine which factor has
   the stronger likely financial/market impact.
5. Use "neutral" when the headline has no clear material directional impact,
   is purely informational, or the impact is genuinely balanced/uncertain.
6. "positive" means the news is likely favorable for the company's stock/financial outlook.
7. "negative" means the news is likely unfavorable for the company's stock/financial outlook.
8. Confidence must represent how certain you are about the classification:
   - 0.90-1.00 = very clear
   - 0.70-0.89 = reasonably clear
   - 0.50-0.69 = uncertain/mixed
   - below 0.50 = highly ambiguous
9. Do NOT calculate a final news_score.
10. Return exactly ONE result for every input ID.
11. Never invent, modify, duplicate, or omit an ID.

Examples:
- "Company beats earnings expectations and raises full-year guidance"
  -> positive
- "Company misses earnings estimates and cuts full-year guidance"
  -> negative
- "Company misses earnings but raises guidance and announces strong future demand"
  -> evaluate the overall context; likely positive if the forward outlook materially outweighs the miss.
- "Company announces date of next quarterly earnings report"
  -> neutral
- "Company faces major regulatory investigation that could materially affect operations"
  -> negative

INPUT:
{json.dumps(prompt_items, indent=2)}

OUTPUT REQUIREMENTS:
Return ONLY a valid JSON array.
No markdown.
No ```json fences.
No explanations.
No additional fields.

Required format:
[
  {{
    "id": 0,
    "sentiment": "positive",
    "confidence": 0.91
  }},
  {{
    "id": 1,
    "sentiment": "negative",
    "confidence": 0.84
  }}
]

Every input ID must appear exactly once in the output.
"""
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0
                )
                content = response.choices[0].message.content.strip()
                if content.startswith("```json"):
                    content = content.replace("```json", "").replace("```", "").strip()
                if content.startswith("```"):
                    content = content.replace("```", "").strip()
                    
                parsed = json.loads(content)
                if not isinstance(parsed, list):
                    raise ValueError("LLM did not return a JSON array.")
                    
                batch_results = []
                for p in parsed:
                    if "id" not in p or "sentiment" not in p or "confidence" not in p:
                        continue
                    sid = p["id"]
                    sent = p["sentiment"].lower()
                    try:
                        conf = float(p["confidence"])
                    except:
                        conf = 0.0
                    
                    if sent not in ["positive", "negative", "neutral"]:
                        sent = "neutral"
                    if conf < 0.0 or conf > 1.0:
                        conf = 0.0
                        
                    batch_results.append({
                        "id": sid,
                        "sentiment": sent,
                        "confidence": conf
                    })
                    
            except Exception as e:
                print(f"LLM sentiment batch failure: {e}")
                batch_results = default_fallback
                
        # Merge back to original items by matching IDs
        result_map = {r["id"]: r for r in batch_results if isinstance(r, dict) and "id" in r}
        
        for idx, original_item in enumerate(batch):
            r = result_map.get(idx)
            if r:
                results.append({
                    "headline": original_item.get("title", ""),
                    "sentiment": r["sentiment"],
                    "confidence": r["confidence"]
                })
            else:
                results.append({
                    "headline": original_item.get("title", ""),
                    "sentiment": "neutral",
                    "confidence": 0.0
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
