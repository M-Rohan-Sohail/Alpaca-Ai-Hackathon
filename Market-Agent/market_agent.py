import os
import json
import logging
import glob
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

# Third-party imports
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class MarketAnalysis:
    """Market analysis result structure"""
    symbol: str
    direction: str  # BULLISH, BEARISH, or NEUTRAL
    confidence: float  # 0.0 to 1.0
    trend_strength: int # 0 to 100
    reasoning: str
    key_factors: list
    timestamp: str
    model_used: str = "gpt-oss-120b"


class MarketAgent:
    """
    Market Agent - Analyzes stock price data and technical indicators
    to determine market direction (BULLISH/BEARISH/NEUTRAL)
    
    Part of the Agentic Layer (Section 5b from the design doc)
    """
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 model: str = "deepseek-ai/DeepSeek-V4-Flash-0731",
                 temperature: float = 0.3,
                 sandbox_mode: bool = False):
        """
        Initialize the Market Agent
        
        Args:
            api_key: Featherless API key (defaults to env var)
            model: LLM model to use
            temperature: LLM temperature (0.0-1.0)
            sandbox_mode: Legacy flag (unused)
        """
        self.model = model
        self.temperature = temperature
        self.sandbox_mode = sandbox_mode
        
        # Initialize LLM client
        api_key = api_key or os.getenv('FEATHERLESS_API_KEY')
        if not api_key:
            raise ValueError("FEATHERLESS_API_KEY is required to run the Market Agent in live mode.")
        
        self.client = OpenAI(api_key=api_key, base_url="https://api.featherless.ai/v1")
        
        # System prompt for the agent
        self.system_prompt = """You are a professional market analyst specializing in technical analysis and market trend identification.

Your role is to analyze the provided price action, technical indicators, and market data to determine the current directional condition of the underlying asset.

IMPORTANT:
* Base your analysis ONLY on the data provided.
* Do not speculate or invent missing information.
* Do not make predictions based on information that is not provided.
* Do not analyze or recommend options strategies.
* Do not consider option-chain data when determining the market direction.
* Your output represents the underlying market thesis that will be passed to downstream agents.

Determine the underlying market direction as one of:
* BULLISH
* BEARISH
* NEUTRAL

Use the following general framework and rules:

BULLISH:
- Price > SMA20
- SMA20 >= SMA50
- RSI > 55
* Price is generally above key moving averages.
* Short-term trend is generally above or strengthening relative to the medium-term trend.
* Momentum indicators provide bullish confirmation.
* Multiple technical signals should preferably support the bullish view.

BEARISH:
- Price < SMA20
- SMA20 <= SMA50
- RSI < 45
* Price is generally below key moving averages.
* Short-term trend is generally below or weakening relative to the medium-term trend.
* Momentum indicators provide bearish confirmation.
* Multiple technical signals should preferably support the bearish view.

NEUTRAL:
- Otherwise
* Technical signals are mixed, contradictory, or insufficient to establish a clear directional bias.

Do not require every indicator to agree before identifying a directional trend. Evaluate the overall technical evidence.

Confidence should reflect the strength and consistency of the available evidence:
* Higher confidence: multiple independent technical signals support the same direction.
* Medium confidence: evidence is directionally supportive but contains some conflicting signals.
* Lower confidence: signals are weak, mixed, or incomplete.

The Market Agent determines the underlying market thesis only. The Options Agent is responsible for determining how that thesis can be expressed through an appropriate options strategy.
"""
    
    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze market data and return trend assessment
        
        Args:
            market_data: Structured data containing:
                - symbol: str
                - price: float
                - trend: dict (sma20, sma50, rsi14)
                - volatility: dict (daily_std, atr)
                - optional: volume, options chain
            
        Returns:
            Dict with: direction, confidence, reasoning, key_factors
        """
        symbol = market_data.get('symbol', 'UNKNOWN')
        logger.info(f"🔍 MarketAgent analyzing {symbol}")
        
        if self.sandbox_mode:
            logger.warning("Sandbox mode is deprecated. Running in live mode.")
        
        try:
            # Build the prompt
            prompt = self._build_prompt(market_data)
            
            # Call LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            result = json.loads(response.choices[0].message.content)
            
            # Validate and enhance
            analysis = self._validate_analysis(result, symbol)
            
            logger.info(f"✅ {symbol}: {analysis['direction']} (confidence: {analysis['confidence']:.2f})")
            logger.debug(f"   Reasoning: {analysis['reasoning']}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ MarketAgent error for {symbol}: {e}")
            return self._get_error_analysis(symbol, str(e))
    
    def _build_prompt(self, data: Dict[str, Any]) -> str:
        """
        Build the LLM prompt from structured data
        """
        symbol = data.get('symbol', 'UNKNOWN')
        price = data.get('price', 0)
        trend = data.get('trend', {})
        volatility = data.get('volatility', {})
        
        # Get indicators with defaults
        sma20 = trend.get('sma20', price)
        sma50 = trend.get('sma50', price)
        rsi14 = trend.get('rsi14', 50)
        atr = volatility.get('atr', 0)
        daily_std = volatility.get('daily_std', 0)
        
        # Calculate some additional metrics
        price_vs_sma20 = ((price - sma20) / sma20 * 100) if sma20 > 0 else 0
        price_vs_sma50 = ((price - sma50) / sma50 * 100) if sma50 > 0 else 0
        
        prompt = f"""Analyze the market data for {symbol}:

**Technical Indicators:**
- Current Price: ${price:.2f}
- 20-day SMA: ${sma20:.2f} ({price_vs_sma20:+.1f}% from price)
- 50-day SMA: ${sma50:.2f} ({price_vs_sma50:+.1f}% from price)
- RSI (14-day): {rsi14:.1f}
- ATR: ${atr:.2f}
- Daily Volatility: {daily_std:.3f}

**Key Relationships:**
- Price vs SMA20: {'ABOVE' if price > sma20 else 'BELOW'}
- Price vs SMA50: {'ABOVE' if price > sma50 else 'BELOW'}
- SMA20 vs SMA50: {'ABOVE' if sma20 > sma50 else 'BELOW'}

Based on this data, determine if {symbol} is BULLISH, BEARISH, or NEUTRAL.

**Return JSON:**
{{
    "direction": "BULLISH|BEARISH|NEUTRAL",
    "confidence": 0.85,
    "trend_strength": 75,
    "reasoning": "Brief explanation of your decision using specific data points",
    "key_factors": ["factor1", "factor2", "factor3"]
}}
NOTE: 'confidence' MUST be a numeric float (e.g., 0.9), NEVER use words like 'nine' or fractions.
'trend_strength' MUST be a numeric integer between 0 and 100."""
        
        return prompt
    
    def _validate_analysis(self, result: Dict, symbol: str) -> Dict[str, Any]:
        """
        Validate and fix analysis results
        """
        # Ensure required fields
        if 'direction' not in result:
            result['direction'] = 'NEUTRAL'
        
        if result['direction'] not in ['BULLISH', 'BEARISH', 'NEUTRAL']:
            result['direction'] = 'NEUTRAL'
        
        if 'confidence' not in result:
            result['confidence'] = 0.5
        
        # Clamp confidence
        result['confidence'] = min(1.0, max(0.0, float(result['confidence'])))
        
        if 'trend_strength' not in result:
            result['trend_strength'] = 50
        result['trend_strength'] = max(0, min(100, int(result['trend_strength'])))
        
        if 'reasoning' not in result:
            result['reasoning'] = 'Analysis completed'
        
        if 'key_factors' not in result or not result['key_factors']:
            result['key_factors'] = ['Data analyzed']
        
        # Add metadata
        result['symbol'] = symbol
        result['timestamp'] = datetime.now().isoformat()
        result['model_used'] = self.model
        
        return result
    

    
    def _get_error_analysis(self, symbol: str, error: str) -> Dict[str, Any]:
        """
        Return error analysis when something goes wrong
        """
        return {
            'symbol': symbol,
            'direction': 'NEUTRAL',
            'confidence': 0.0,
            'trend_strength': 0,
            'reasoning': f'Error occurred during analysis: {error}',
            'key_factors': ['Error in analysis'],
            'timestamp': datetime.now().isoformat(),
            'model_used': self.model,
            'error': error
        }


# ============================================
# CLI / Standalone Usage
# ============================================

def main():
    """
    Standalone test for Market Agent
    """
    print("🚀 Market Agent - Alpaca AI Hackathon 2026")
    print("=" * 50)
    
    # Find the latest scanner output
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
        
    candidates = scanner_data.get("overall_ranking", {}).get("candidates", [])
    if not candidates:
        print("❌ No candidates found in the scanner output.")
        return
    
    # Initialize agent
    print("📊 Initializing Market Agent...")
    agent = MarketAgent(
        sandbox_mode=False  # Use mock responses for quick testing
    )
    
    all_results = []
    
    print("\n🔍 Running analysis on candidates...")
    for candidate in candidates:
        symbol = candidate.get("symbol", "UNKNOWN")
        print(f"\n--- Analyzing {symbol} ---")
        result = agent.analyze(candidate)
        all_results.append(result)
        
        # Display results
        print(f"   Direction: {result['direction']}")
        print(f"   Confidence: {result['confidence']:.2%}")
        print(f"   Trend Strength: {result['trend_strength']}")
        print(f"   Reasoning: {result['reasoning']}")
        print(f"   Key Factors: {', '.join(result['key_factors'])}")
        
    # Save to file
    output_dir = os.path.join(base_dir, "..", "SAVE-DATA-PER-AGENT", "Market-Agent-Output")
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_dir, f"agent_analysis_{timestamp}.json")
    
    output_data = {
        "run_timestamp": timestamp,
        "analyses": all_results
    }
    
    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2)
    print(f"\n💾 All results saved to {filename}")
    
    return all_results


if __name__ == "__main__":
    main()