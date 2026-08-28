import os
import sys
import json
import logging
import glob
import requests
from datetime import datetime
from typing import Dict, Any, List
import time

from groq import Groq
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NewsAgent:
    def __init__(self, model="qwen/qwen3.8-27b", sandbox_mode=False):
        self.model = model
        self.sandbox_mode = sandbox_mode
        self.serper_api_key = os.getenv("SERPER_API_KEY")
        
        if not sandbox_mode:
            self.client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        else:
            self.client = None

    def fetch_news_from_serper(self, symbol: str) -> List[Dict[str, Any]]:
        """Fetch news articles from Serper API."""
        if self.sandbox_mode:
            logger.info(f"Sandbox mode: returning mock news for {symbol}")
            return [
                {"title": f"{symbol} announces new product", "link": "https://example.com/1", "source": "Reuters", "date": "1 hour ago", "snippet": "Company announces huge new product."},
                {"title": f"{symbol} announces new product - details", "link": "https://example.com/2", "source": "Bloomberg", "date": "2 hours ago", "snippet": "More details on the new product."},
                {"title": f"{symbol} faces regulatory headwind", "link": "https://example.com/3", "source": "Yahoo Finance", "date": "1 day ago", "snippet": "Regulators are looking into the company."}
            ]

        url = "https://google.serper.dev/news"
        payload = json.dumps({
            "q": f"{symbol} stock news",
            "num": 10
        })
        headers = {
            'X-API-KEY': self.serper_api_key,
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(url, headers=headers, data=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("news", [])
        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {e}")
            return []

    def deduplicate_urls(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Stage 1: Deduplicate by exact URL."""
        seen = set()
        unique = []
        for article in articles:
            url = article.get("link", "")
            if url and url not in seen:
                seen.add(url)
                unique.append(article)
        return unique

    def semantic_deduplication(self, articles: List[Dict[str, Any]], symbol: str) -> Dict[str, str]:
        """Stage 2: LLM Call 1 - Group articles into events."""
        if not articles:
            return {}
            
        if self.sandbox_mode:
            return {a.get("link"): f"event_{i%2}" for i, a in enumerate(articles)}

        articles_summary = []
        for i, a in enumerate(articles):
            articles_summary.append(f"[{i}] URL: {a.get('link')}\nHeadline: {a.get('title')}\nSnippet: {a.get('snippet')}\n")
            
        prompt = f"""
You are a financial news assistant. I have a list of news articles for {symbol}. 
Your task is to perform semantic deduplication: identify which articles describe the EXACT SAME underlying news event, and assign them the same event ID (e.g., 'event_1', 'event_2').

Articles:
{''.join(articles_summary)}

Respond ONLY in valid JSON format mapping the exact URL to its assigned event_id. Do not include markdown formatting.
Example:
{{
    "https://example.com/1": "event_1",
    "https://example.com/2": "event_1",
    "https://example.com/3": "event_2"
}}
"""
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=4000,
                    response_format={"type": "json_object"}
                )
                result = json.loads(response.choices[0].message.content)
                return result
            except Exception as e:
                logger.error(f"Error in semantic deduplication for {symbol} (Attempt {attempt}/{max_retries}): {e}")
                if attempt == max_retries:
                    logger.critical("Max retries reached. Terminating process to prevent garbage data.")
                    sys.exit(1)
                logger.info("Sleeping for 20s before retrying...")
                time.sleep(20)

    def analyze_events(self, articles: List[Dict], event_mapping: Dict[str, str], symbol: str) -> Dict[str, Any]:
        """LLM Call 2 - Final analysis generation."""
        if not articles:
            return {}

        articles_data = []
        for a in articles:
            url = a.get("link", "")
            articles_data.append({
                "url": url,
                "headline": a.get("title", ""),
                "source": a.get("source", ""),
                "date": a.get("date", ""),
                "snippet": a.get("snippet", ""),
                "event_id": event_mapping.get(url, "event_unknown")
            })

        prompt = f"""
You are a financial analyst. Analyze these news articles for {symbol}. The articles have already been grouped into events.

Criteria for Relevance Score (0-100):
- Entity Relevance (30%): Is {symbol} actually involved?
- Market Materiality (30%): Could this affect the stock?
- Specificity (20%): Is it about {symbol} specifically?
- Recency (10%): Is it recent?
- Source Quality (10%): Is the source credible?

Generate an analysis in EXACTLY this JSON structure:
{{
  "articles": [
    {{
      "url": "...",
      "relevance_score": 92,
      "sentiment": "positive",
      "impact": "high",
      "event_id": "event_1"
    }}
  ],
  "events": [
    {{
      "event_id": "event_1",
      "event_type": "earnings",
      "sentiment": "positive",
      "impact": "high",
      "headline": "Representative headline for this event",
      "source": "Best source for this event",
      "url": "URL of the best source",
      "published_at": "Publish date of the best source"
    }}
  ],
  "overall_sentiment": "positive",
  "catalysts": ["catalyst 1"],
  "risks": ["risk 1"]
}}

Articles:
{json.dumps(articles_data, indent=2)}
"""

        if self.sandbox_mode:
            return {
                "articles": [{"url": a["url"], "relevance_score": 85, "sentiment": "positive", "impact": "high", "event_id": a["event_id"]} for a in articles_data],
                "events": [{"event_id": "event_0", "event_type": "product_launch", "sentiment": "positive", "impact": "high", "headline": "New product", "source": "Reuters", "url": "https://example.com", "published_at": "1 hour ago"}],
                "overall_sentiment": "positive", "catalysts": ["New product"], "risks": []
            }

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=4000,
                    response_format={"type": "json_object"}
                )
                return json.loads(response.choices[0].message.content)
            except Exception as e:
                logger.error(f"Error in analysis for {symbol} (Attempt {attempt}/{max_retries}): {e}")
                if attempt == max_retries:
                    logger.critical("Max retries reached. Terminating process to prevent garbage data.")
                    sys.exit(1)
                logger.info("Sleeping for 20s before retrying...")
                time.sleep(20)

    def calculate_python_news_score(self, llm_analysis: Dict[str, Any], original_articles: List[Dict]) -> float:
        """Calculate final news score using hardcoded python rules per article and averaging them."""
        # Weights
        W_SENTIMENT = 0.30
        W_IMPACT = 0.25
        W_RELEVANCE = 0.20
        W_RECENCY = 0.15
        W_SOURCE = 0.10
        
        # Lookups
        sentiment_map = {"positive": 100, "neutral": 50, "negative": 0}
        impact_map = {"high": 100, "medium": 50, "low": 0}
        
        # High quality sources
        premium_sources = ["reuters", "bloomberg", "wall street journal", "wsj", "cnbc", "financial times"]
        good_sources = ["yahoo finance", "marketwatch", "seeking alpha", "motley fool", "barron's"]

        article_scores = []
        
        # Build url to original article map for source and date
        orig_map = {a.get("link"): a for a in original_articles}

        articles_analyzed = llm_analysis.get("articles", [])
        for a in articles_analyzed:
            url = a.get("url", "")
            sentiment = a.get("sentiment", "neutral").lower()
            impact = a.get("impact", "medium").lower()
            relevance = a.get("relevance_score", 50)
            
            orig = orig_map.get(url, {})
            source = str(orig.get("source", "")).lower()
            date_str = str(orig.get("date", "")).lower()

            # Sentiment & Impact
            s_score = sentiment_map.get(sentiment, 50)
            i_score = impact_map.get(impact, 50)
            r_score = float(relevance)
            
            # Source Score
            if any(ps in source for ps in premium_sources):
                src_score = 100
            elif any(gs in source for gs in good_sources):
                src_score = 80
            else:
                src_score = 50

            # Recency Score
            if "hour" in date_str or "min" in date_str or "today" in date_str or "sec" in date_str:
                rec_score = 100
            elif "day" in date_str:
                rec_score = 80
            elif "week" in date_str:
                rec_score = 50
            else:
                rec_score = 20

            total = (s_score * W_SENTIMENT) + (i_score * W_IMPACT) + (r_score * W_RELEVANCE) + (rec_score * W_RECENCY) + (src_score * W_SOURCE)
            article_scores.append(total)

        if not article_scores:
            return 50.0

        return sum(article_scores) / len(article_scores)

    def process_asset(self, symbol: str) -> Dict[str, Any]:
        """Full pipeline for a single asset."""
        logger.info(f"Fetching news for {symbol}...")
        raw_articles = self.fetch_news_from_serper(symbol)
        
        logger.info(f"Deduplicating URLs for {symbol}...")
        unique_articles = self.deduplicate_urls(raw_articles)
        
        logger.info(f"Running semantic deduplication for {symbol}...")
        event_mapping = self.semantic_deduplication(unique_articles, symbol)
        
        if not self.sandbox_mode:
            logger.info("⏳ Cooldown (10s) before final analysis to avoid API rate limits...")
            time.sleep(10)
        
        logger.info(f"Running final analysis for {symbol}...")
        llm_analysis = self.analyze_events(unique_articles, event_mapping, symbol)
        
        logger.info(f"Calculating python news score for {symbol}...")
        final_score = self.calculate_python_news_score(llm_analysis, unique_articles)

        # Build final specific output structure requested by user
        final_output = {
            "symbol": symbol,
            "news_score": round(final_score, 1),
            "overall_sentiment": llm_analysis.get("overall_sentiment", "neutral"),
            "overall_impact": llm_analysis.get("events", [{}])[0].get("impact", "medium") if llm_analysis.get("events") else "medium",
            "relevant_news_count": len(llm_analysis.get("articles", [])),
            "catalysts": llm_analysis.get("catalysts", []),
            "risks": llm_analysis.get("risks", []),
            "events": []
        }
        
        # Merge LLM article-level data with event-level data
        for ev in llm_analysis.get("events", []):
            final_output["events"].append({
                "headline": ev.get("headline", ""),
                "source": ev.get("source", ""),
                "url": ev.get("url", ""),
                "published_at": ev.get("published_at", ""),
                "relevance_score": 100, # Handled per article in python normally, fallback for event
                "sentiment": ev.get("sentiment", "neutral"),
                "impact": ev.get("impact", "medium"),
                "event_type": ev.get("event_type", "unknown")
            })

        return final_output


def main():
    print("🚀 News Agent - Alpaca AI Hackathon 2026")
    print("=" * 50)
    
    # 1. Find the latest scanner output
    base_dir = os.path.dirname(os.path.abspath(__file__))
    scanner_dir = os.path.join(base_dir, "..", "SAVE-DATA-PER-AGENT", "Deterministic-Filter-Output")
    
    json_files = glob.glob(os.path.join(scanner_dir, "*.json"))
    if not json_files:
        print(f"❌ No scanner output found in {scanner_dir}")
        return
        
    latest_file = max(json_files, key=os.path.getctime)
    print(f"📄 Found latest scanner output: {os.path.basename(latest_file)}")
    
    with open(latest_file, 'r') as f:
        scanner_data = json.load(f)
        
    # The scanner output has overall_ranking inside output 2, wait, 
    # The user mentioned: output of the market scanner i.e ({"detailed_scores": {"candidates": [{"symbol": "NVDA", "rank": 1...}]}})
    # Let's dynamically extract it
    candidates = []
    if "detailed_scores" in scanner_data:
        candidates = scanner_data["detailed_scores"].get("candidates", [])
    elif "overall_ranking" in scanner_data:
        candidates = scanner_data["overall_ranking"].get("candidates", [])
        
    if not candidates:
        print("❌ No candidates found in the scanner output.")
        return
        
    agent = NewsAgent(sandbox_mode=False) # Set to False when API keys are ready
    
    all_analysis = []
    
    for candidate in candidates:
        symbol = candidate.get("symbol")
        if not symbol: continue
        
        print(f"\n--- Processing News for {symbol} ---")
        result = agent.process_asset(symbol)
        all_analysis.append(result)
        
        if not agent.sandbox_mode and candidate != candidates[-1]:
            print("⏳ Cooldown (15s) before processing next asset...")
            time.sleep(15)
        
    # Save Output
    output_dir = os.path.join(base_dir, "..", "SAVE-DATA-PER-AGENT", "News-Agent-Output")
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_dir, f"news_analysis_{timestamp}.json")
    
    final_payload = {
        "run_timestamp": timestamp,
        "news_analysis": all_analysis
    }
    
    with open(filename, 'w') as f:
        json.dump(final_payload, f, indent=2)
        
    print(f"\n💾 Saved News Agent output to {filename}")

if __name__ == "__main__":
    main()
