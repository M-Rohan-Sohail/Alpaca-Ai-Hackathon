#!/usr/bin/env python
"""
Decision Agent - Aggregates all agent outputs and makes final TRADE/PASS decision
Part of Alpaca AI Hackathon 2026 - Section 5e
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass

from groq import Groq
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
class PortfolioState:
    """Portfolio state for decision making"""
    account_equity: float = 100000.0
    cash: float = 70000.0
    buying_power: float = 65000.0
    open_positions: List[Dict] = None
    total_exposure: float = 0.0
    total_risk: float = 0.0
    
    def __post_init__(self):
        if self.open_positions is None:
            self.open_positions = []


@dataclass
class RiskConstraints:
    """Risk constraints from user config"""
    max_trade_allocation_pct: float = 5.0
    max_total_exposure_pct: float = 20.0
    max_account_risk_pct: float = 1.0


class DecisionAgent:
    """
    Decision Agent - Aggregates all agent outputs and makes final TRADE/PASS decision
    """
    
    def __init__(self,
                 api_key: Optional[str] = None,
                 model: str = "openai/gpt-oss-120b",
                 temperature: float = 0.2,
                 sandbox_mode: bool = True,
                 portfolio: Optional[PortfolioState] = None,
                 risk_constraints: Optional[RiskConstraints] = None):
        
        self.model = model
        self.temperature = temperature
        self.sandbox_mode = sandbox_mode
        
        self.portfolio = portfolio or PortfolioState()
        self.risk_constraints = risk_constraints or RiskConstraints()
        
        if not sandbox_mode:
            try:
                api_key = api_key or os.getenv('GROQ_API_KEY')
                if not api_key:
                    logger.warning("⚠️ No GROQ_API_KEY found. Switching to SANDBOX mode.")
                    self.sandbox_mode = True
                    self.client = None
                else:
                    self.client = Groq(api_key=api_key)
                    logger.info("✅ Groq client initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Groq: {e}")
                self.sandbox_mode = True
                self.client = None
        else:
            self.client = None
            logger.info("🔧 Running in SANDBOX mode")
    
    def decide(self, symbol: str, market: Dict, news: Dict, options: Dict) -> Dict:
        """Make final trading decision"""
        logger.info(f"🤔 DecisionAgent making final decision for {symbol}")
        
        if self.sandbox_mode:
            return self._get_mock_decision(symbol, market, news, options)
        
        try:
            prompt = self._build_prompt(symbol, market, news, options)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a senior portfolio manager."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            decision = self._validate_decision(result, symbol)
            logger.info(f"✅ {symbol}: {decision['decision']} ({decision['confidence']:.2%})")
            return decision
        except Exception as e:
            logger.error(f"❌ DecisionAgent error: {e}")
            return self._get_error_decision(symbol, str(e))
    
    def _build_prompt(self, symbol: str, market: Dict, news: Dict, options: Dict) -> str:
        """Build LLM prompt"""
        return f"""
Analyze data for {symbol}:

MARKET: {market.get('direction')} (Confidence: {market.get('confidence', 0.5):.2%})
NEWS: Score {news.get('news_score', 0):.1f}, Sentiment: {news.get('overall_sentiment')}
OPTIONS: {options.get('strategy_type')}, R/R: {options.get('risk_reward_ratio', 0):.2f}

PORTFOLIO:
- Equity: ${self.portfolio.account_equity:,.2f}
- Cash: ${self.portfolio.cash:,.2f}
- Risk: ${self.portfolio.total_risk:,.2f}

Constraints: {self.risk_constraints.max_trade_allocation_pct}% per trade, {self.risk_constraints.max_account_risk_pct}% account risk

Decide TRADE or PASS. Return JSON:
{{"decision": "TRADE|PASS", "strategy_type": "...", "legs": [], "confidence": 0.85, "reasoning": "..."}}
"""
    
    def _validate_decision(self, result: Dict, symbol: str) -> Dict:
        result['symbol'] = symbol
        result['timestamp'] = datetime.now().isoformat()
        if 'confidence' not in result:
            result['confidence'] = 0.5
        result['confidence'] = min(1.0, max(0.0, float(result['confidence'])))
        return result
    
    def _get_mock_decision(self, symbol: str, market: Dict, news: Dict, options: Dict) -> Dict:
        """Mock decision for sandbox mode"""
        market_direction = market.get('direction', 'NEUTRAL')
        market_conf = market.get('confidence', 0.5)
        news_score = news.get('news_score', 50)
        options_rr = options.get('risk_reward_ratio', 0)
        
        should_trade = (
            market_direction in ['BULLISH', 'BEARISH'] and
            market_conf > 0.6 and
            news_score > 60 and
            options_rr > 1.5
        )
        
        if should_trade:
            return {
                'symbol': symbol,
                'decision': 'TRADE',
                'strategy_type': options.get('strategy_type', 'BullCallSpread'),
                'legs': options.get('legs', []),
                'confidence': 0.85,
                'reasoning': f'Mock decision: {market_direction} market, positive news, R/R {options_rr:.2f}',
                'timestamp': datetime.now().isoformat(),
                'model_used': 'mock'
            }
        else:
            return {
                'symbol': symbol,
                'decision': 'PASS',
                'confidence': 0.45,
                'reasoning': 'Mock decision: PASS - insufficient alignment',
                'timestamp': datetime.now().isoformat(),
                'model_used': 'mock'
            }
    
    def _get_error_decision(self, symbol: str, error: str) -> Dict:
        return {
            'symbol': symbol,
            'decision': 'PASS',
            'confidence': 0.0,
            'reasoning': f'Error: {error}',
            'timestamp': datetime.now().isoformat(),
            'error': error
        }


def main():
    print("🚀 Decision Agent Test")
    print("=" * 40)
    
    agent = DecisionAgent(sandbox_mode=True)
    
    result = agent.decide(
        "NVDA",
        {"direction": "BULLISH", "confidence": 0.85, "reasoning": "Strong", "key_factors": []},
        {"news_score": 84.5, "overall_sentiment": "positive", "overall_impact": "high", "catalysts": [], "risks": []},
        {"strategy_type": "BullCallSpread", "confidence": 0.89, "legs": [], "risk_reward_ratio": 3.17, "estimated_max_loss": 240, "estimated_max_profit": 760}
    )
    
    print(f"\n📊 Result:")
    print(f"   Symbol: {result['symbol']}")
    print(f"   Decision: {result['decision']}")
    print(f"   Confidence: {result['confidence']:.2%}")
    print(f"   Reason: {result['reasoning']}")

if __name__ == "__main__":
    main()