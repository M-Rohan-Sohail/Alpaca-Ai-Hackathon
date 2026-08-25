#!/usr/bin/env python
"""
Market Agent - Analyzes price patterns and indicators
Part of Alpaca AI Hackathon 2026

Author: [Your Name]
Team: [Team Name]
Component: Agentic Layer - Market Agent (5b)
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

# Third-party imports
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
    reasoning: str
    key_factors: list
    timestamp: str
    model_used: str = "gpt-4"


class MarketAgent:
    """
    Market Agent - Analyzes stock price data and technical indicators
    to determine market direction (BULLISH/BEARISH/NEUTRAL)
    
    Part of the Agentic Layer (Section 5b from the design doc)
    """
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 model: str = "gpt-4",
                 temperature: float = 0.3,
                 sandbox_mode: bool = True):
        """
        Initialize the Market Agent
        
        Args:
            api_key: OpenAI API key (defaults to env var)
            model: LLM model to use
            temperature: LLM temperature (0.0-1.0)
            sandbox_mode: If True, use mock responses (for testing)
        """
        self.model = model
        self.temperature = temperature
        self.sandbox_mode = sandbox_mode
        
        # Initialize LLM client
        if not sandbox_mode:
            self.client = OpenAI(
                api_key=api_key or os.getenv('OPENAI_API_KEY')
            )
        else:
            self.client = None
            logger.info("Running in SANDBOX mode - using mock responses")
        
        # System prompt for the agent
        self.system_prompt = """You are a professional market analyst specializing in technical analysis.
Your role is to analyze price action and indicators to determine market trends.
Always base your analysis on the provided data, not speculation.

Rules:
1. BULLISH if: price > SMA20 > SMA50 AND RSI > 60
2. BEARISH if: price < SMA20 < SMA50 AND RSI < 40
3. NEUTRAL otherwise (but consider other factors)

Provide reasoning for your decision with specific data points.
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
            return self._get_mock_analysis(market_data)
        
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

**Decision Rules (use as guidelines):**
- BULLISH: Price > SMA20 > SMA50 AND RSI > 60
- BEARISH: Price < SMA20 < SMA50 AND RSI < 40
- NEUTRAL: Mixed signals or range-bound

**Return JSON:**
{{
    "direction": "BULLISH|BEARISH|NEUTRAL",
    "confidence": 0.85,
    "reasoning": "Brief explanation of your decision using specific data points",
    "key_factors": ["factor1", "factor2", "factor3"]
}}"""
        
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
        
        if 'reasoning' not in result:
            result['reasoning'] = 'Analysis completed'
        
        if 'key_factors' not in result or not result['key_factors']:
            result['key_factors'] = ['Data analyzed']
        
        # Add metadata
        result['symbol'] = symbol
        result['timestamp'] = datetime.now().isoformat()
        result['model_used'] = self.model
        
        return result
    
    def _get_mock_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate mock analysis for sandbox/testing mode
        """
        symbol = data.get('symbol', 'UNKNOWN')
        price = data.get('price', 100)
        trend = data.get('trend', {})
        sma20 = trend.get('sma20', price - 5)
        sma50 = trend.get('sma50', price - 10)
        rsi14 = trend.get('rsi14', 55)
        
        # Simple deterministic logic for mock
        if price > sma20 > sma50 and rsi14 > 55:
            direction = 'BULLISH'
            confidence = 0.75 + (rsi14 - 55) / 100
            factors = ['Price above SMAs', 'RSI trending up']
        elif price < sma20 < sma50 and rsi14 < 45:
            direction = 'BEARISH'
            confidence = 0.75 + (45 - rsi14) / 100
            factors = ['Price below SMAs', 'RSI trending down']
        else:
            direction = 'NEUTRAL'
            confidence = 0.5
            factors = ['Mixed signals', 'Sideways trend']
        
        return {
            'symbol': symbol,
            'direction': direction,
            'confidence': min(1.0, confidence),
            'reasoning': f'Mock analysis: {direction} based on indicators',
            'key_factors': factors,
            'timestamp': datetime.now().isoformat(),
            'model_used': 'mock'
        }
    
    def _get_error_analysis(self, symbol: str, error: str) -> Dict[str, Any]:
        """
        Return error analysis when something goes wrong
        """
        return {
            'symbol': symbol,
            'direction': 'NEUTRAL',
            'confidence': 0.0,
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
    
    # Sample test data
    test_data = {
        "symbol": "NVDA",
        "price": 180.45,
        "trend": {
            "sma20": 178.20,
            "sma50": 173.50,
            "rsi14": 68.0
        },
        "volatility": {
            "daily_std": 0.018,
            "atr": 4.20
        },
        "volume": {
            "today": 34000000,
            "avg20": 25000000
        }
    }
    
    # Initialize agent
    print("📊 Initializing Market Agent...")
    agent = MarketAgent(
        sandbox_mode=True  # Use mock responses for quick testing
    )
    
    # Run analysis
    print("\n🔍 Running analysis on NVDA...")
    result = agent.analyze(test_data)
    
    # Display results
    print("\n📈 Analysis Results:")
    print(f"   Symbol: {result['symbol']}")
    print(f"   Direction: {result['direction']}")
    print(f"   Confidence: {result['confidence']:.2%}")
    print(f"   Reasoning: {result['reasoning']}")
    print(f"   Key Factors: {', '.join(result['key_factors'])}")
    
    # Save to file
    with open('market_analysis.json', 'w') as f:
        json.dump(result, f, indent=2)
    print(f"\n💾 Results saved to market_analysis.json")
    
    return result


if __name__ == "__main__":
    main()