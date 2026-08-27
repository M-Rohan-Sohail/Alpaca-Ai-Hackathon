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
from dataclasses import dataclass, asdict

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
    max_trade_allocation_pct: float = 5.0  # Max % of portfolio per trade
    max_total_exposure_pct: float = 20.0   # Max % of portfolio total exposure
    max_account_risk_pct: float = 1.0      # Max % of account risk per trade


class DecisionAgent:
    """
    Decision Agent - Aggregates all agent outputs and makes final TRADE/PASS decision
    
    Part of the Agentic Layer (Section 5e from the design doc)
    
    Responsibilities:
    1. Aggregate Market/News/Options agent outputs
    2. Check directional alignment
    3. Evaluate signal strength
    4. Consider portfolio context
    5. Make TRADE/PASS decision with reasoning
    """
    
    def __init__(self,
                 api_key: Optional[str] = None,
                 model: str = "openai/gpt-oss-120b",
                 temperature: float = 0.2,
                 sandbox_mode: bool = True,
                 portfolio: Optional[PortfolioState] = None,
                 risk_constraints: Optional[RiskConstraints] = None):
        """
        Initialize the Decision Agent
        
        Args:
            api_key: Groq API key
            model: LLM model to use
            temperature: LLM temperature (0.0-1.0)
            sandbox_mode: If True, use mock responses
            portfolio: Portfolio state
            risk_constraints: Risk constraints
        """
        self.model = model
        self.temperature = temperature
        self.sandbox_mode = sandbox_mode
        
        # Initialize portfolio state
        self.portfolio = portfolio or PortfolioState()
        self.risk_constraints = risk_constraints or RiskConstraints()
        
        # Initialize LLM client
        if not sandbox_mode:
            self.client = Groq(
                api_key=api_key or os.getenv('GROQ_API_KEY')
            )
        else:
            self.client = None
            logger.info("Running in SANDBOX mode - using mock responses")
        
        # System prompt for the agent
        self.system_prompt = """You are a senior portfolio manager making final trading decisions.
Your role is to aggregate all analysis and make prudent decisions.
Risk management is your top priority. When in doubt, PASS.

Decision Criteria:
1. Directional Alignment: Market, News, and Options must align
2. Signal Strength: Confidence scores should be high (>0.6)
3. Risk/Reward: Must be attractive (>1.5)
4. Portfolio Context: Consider existing positions and exposure
5. Risk Constraints: Respect max allocation, exposure, and account risk

Always provide clear reasoning for your decision.
"""
    
    def decide(self, 
               symbol: str,
               market_analysis: Dict[str, Any],
               news_analysis: Dict[str, Any],
               options_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make final trading decision for a single candidate
        
        Args:
            symbol: Stock symbol
            market_analysis: Output from Market Agent
            news_analysis: Output from News Agent
            options_analysis: Output from Options Agent
            
        Returns:
            Decision dict with TRADE/PASS decision
        """
        logger.info(f"🤔 DecisionAgent making final decision for {symbol}")
        
        if self.sandbox_mode:
            return self._get_mock_decision(symbol, market_analysis, news_analysis, options_analysis)
        
        try:
            # Build the prompt
            prompt = self._build_prompt(symbol, market_analysis, news_analysis, options_analysis)
            
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
            decision = self._validate_decision(result, symbol)
            
            logger.info(f"✅ {symbol}: {decision['decision']} (confidence: {decision['confidence']:.2f})")
            logger.debug(f"   Reasoning: {decision['reasoning']}")
            
            return decision
            
        except Exception as e:
            logger.error(f"❌ DecisionAgent error for {symbol}: {e}")
            return self._get_error_decision(symbol, str(e))
    
    def _build_prompt(self, symbol: str, 
                      market: Dict[str, Any],
                      news: Dict[str, Any],
                      options: Dict[str, Any]) -> str:
        """
        Build the LLM prompt from all agent outputs
        """
        # Extract key information
        market_direction = market.get('direction', 'NEUTRAL')
        market_confidence = market.get('confidence', 0.5)
        market_factors = market.get('key_factors', [])
        market_reasoning = market.get('reasoning', '')
        
        news_score = news.get('news_score', 50.0)
        news_sentiment = news.get('overall_sentiment', 'neutral')
        news_impact = news.get('overall_impact', 'medium')
        news_catalysts = news.get('catalysts', [])
        news_risks = news.get('risks', [])
        
        options_strategy = options.get('strategy_type', 'PASS')
        options_confidence = options.get('confidence', 0.5)
        options_legs = options.get('legs', [])
        options_rr = options.get('risk_reward_ratio', 0)
        options_max_loss = options.get('estimated_max_loss', 0)
        options_max_profit = options.get('estimated_max_profit', 0)
        options_reasoning = options.get('reasoning', '')
        
        # Format legs for prompt
        legs_str = ""
        for leg in options_legs:
            legs_str += f"  - {leg.get('action')} {leg.get('option_type')} @ ${leg.get('strike')}\n"
        
        prompt = f"""
You are the Decision Agent for {symbol}. Analyze the following data and decide TRADE or PASS.

## 📊 Market Analysis
- Direction: {market_direction}
- Confidence: {market_confidence:.2%}
- Reasoning: {market_reasoning}
- Key Factors: {', '.join(market_factors)}

## 📰 News Analysis
- Score: {news_score:.1f}
- Sentiment: {news_sentiment.upper()}
- Impact: {news_impact.upper()}
- Catalysts: {', '.join(news_catalysts) if news_catalysts else 'None identified'}
- Risks: {', '.join(news_risks) if news_risks else 'None identified'}

## 💼 Options Strategy
- Strategy: {options_strategy}
- Confidence: {options_confidence:.2%}
- Legs:
{legs_str if legs_str else '  - No legs specified'}
- Risk/Reward: {options_rr:.2f}
- Max Loss: ${options_max_loss:.2f}
- Max Profit: ${options_max_profit:.2f}
- Reasoning: {options_reasoning}

## 💰 Portfolio State
- Account Equity: ${self.portfolio.account_equity:,.2f}
- Cash Available: ${self.portfolio.cash:,.2f}
- Buying Power: ${self.portfolio.buying_power:,.2f}
- Open Positions: {len(self.portfolio.open_positions)}
- Total Exposure: ${self.portfolio.total_exposure:,.2f} ({self.portfolio.total_exposure/self.portfolio.account_equity*100:.1f}%)
- Total Risk: ${self.portfolio.total_risk:,.2f} ({self.portfolio.total_risk/self.portfolio.account_equity*100:.2f}%)

## 🔒 Risk Constraints
- Max Per-Trade Allocation: {self.risk_constraints.max_trade_allocation_pct}%
- Max Total Exposure: {self.risk_constraints.max_total_exposure_pct}%
- Max Account Risk Per Trade: {self.risk_constraints.max_account_risk_pct}%

---

## Decision Criteria:
1. **Directional Alignment**: Are Market, News, and Options all aligned?
2. **Signal Strength**: Are confidence scores > 0.6?
3. **Risk/Reward**: Is R/R > 1.5?
4. **Portfolio Fit**: Can we accommodate this trade?
5. **Risk Constraints**: Does this trade violate any limits?

## Return JSON:
{{
    "decision": "TRADE|PASS",
    "strategy_type": "BullCallSpread|BearPutSpread|LongCall|LongPut|PASS",
    "legs": [
        {{
            "action": "BUY|SELL",
            "option_type": "CALL|PUT",
            "strike": 0.0,
            "expiration": "YYYY-MM-DD"
        }}
    ],
    "confidence": 0.85,
    "reasoning": "Brief explanation of why TRADE or PASS",
    "risk_assessment": {{
        "status": "ACCEPTABLE|UNACCEPTABLE",
        "max_loss_per_contract": 0.0,
        "max_profit_per_contract": 0.0,
        "risk_reward_ratio": 0.0
    }}
}}

NOTE: 'confidence' MUST be a numeric float (e.g., 0.9), NEVER use words like 'nine' or fractions."""
        
        return prompt
    
    def _validate_decision(self, result: Dict, symbol: str) -> Dict[str, Any]:
        """
        Validate and enhance the decision
        """
        # Ensure required fields
        if 'decision' not in result:
            result['decision'] = 'PASS'
        
        if result['decision'] not in ['TRADE', 'PASS']:
            result['decision'] = 'PASS'
        
        # For PASS decisions, simplify
        if result['decision'] == 'PASS':
            return {
                'symbol': symbol,
                'decision': 'PASS',
                'confidence': result.get('confidence', 0.5),
                'reasoning': result.get('reasoning', 'Decision to pass based on analysis'),
                'timestamp': datetime.now().isoformat(),
                'model_used': self.model
            }
        
        # For TRADE decisions, validate strategy
        if 'strategy_type' not in result:
            result['strategy_type'] = 'PASS'
        
        if 'legs' not in result:
            result['legs'] = []
        
        if 'confidence' not in result:
            result['confidence'] = 0.5
        
        # Clamp confidence
        result['confidence'] = min(1.0, max(0.0, float(result['confidence'])))
        
        if 'reasoning' not in result:
            result['reasoning'] = 'Decision based on analysis'
        
        if 'risk_assessment' not in result:
            result['risk_assessment'] = {
                'status': 'ACCEPTABLE',
                'max_loss_per_contract': 0,
                'max_profit_per_contract': 0,
                'risk_reward_ratio': 0
            }
        
        # Add metadata
        result['symbol'] = symbol
        result['timestamp'] = datetime.now().isoformat()
        result['model_used'] = self.model
        
        return result
    
    def _get_mock_decision(self, symbol: str, 
                           market: Dict[str, Any],
                           news: Dict[str, Any],
                           options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate mock decision for sandbox mode
        """
        market_direction = market.get('direction', 'NEUTRAL')
        market_confidence = market.get('confidence', 0.5)
        news_score = news.get('news_score', 50)
        news_sentiment = news.get('overall_sentiment', 'neutral')
        options_rr = options.get('risk_reward_ratio', 0)
        options_strategy = options.get('strategy_type', 'PASS')
        options_legs = options.get('legs', [])
        
        # Decision logic
        should_trade = (
            market_direction in ['BULLISH', 'BEARISH'] and
            market_confidence > 0.6 and
            news_score > 60 and
            news_sentiment in ['positive', 'negative'] and
            options_rr > 1.5 and
            options_strategy != 'PASS'
        )
        
        # Check portfolio constraints
        new_risk = options.get('estimated_max_loss', 0)
        total_risk = self.portfolio.total_risk + new_risk
        max_account_risk = self.portfolio.account_equity * (self.risk_constraints.max_account_risk_pct / 100)
        
        if total_risk > max_account_risk:
            should_trade = False
        
        if should_trade:
            return {
                'symbol': symbol,
                'decision': 'TRADE',
                'strategy_type': options_strategy,
                'legs': options_legs,
                'confidence': min(0.95, (market_confidence + options.get('confidence', 0.5)) / 2 + 0.1),
                'reasoning': f'Mock decision: {market_direction} market, positive news, attractive R/R {options_rr:.2f}',
                'risk_assessment': {
                    'status': 'ACCEPTABLE',
                    'max_loss_per_contract': options.get('estimated_max_loss', 0),
                    'max_profit_per_contract': options.get('estimated_max_profit', 0),
                    'risk_reward_ratio': options_rr
                },
                'timestamp': datetime.now().isoformat(),
                'model_used': 'mock'
            }
        else:
            return {
                'symbol': symbol,
                'decision': 'PASS',
                'confidence': 0.5 + (market_confidence - 0.5) * 0.5,
                'reasoning': f'Mock decision: PASS - insufficient alignment or risk constraints',
                'timestamp': datetime.now().isoformat(),
                'model_used': 'mock'
            }
    
    def _get_error_decision(self, symbol: str, error: str) -> Dict[str, Any]:
        """
        Return error decision when something goes wrong
        """
        return {
            'symbol': symbol,
            'decision': 'PASS',
            'confidence': 0.0,
            'reasoning': f'Error occurred during decision: {error}',
            'timestamp': datetime.now().isoformat(),
            'model_used': self.model,
            'error': error
        }
    
    def decide_batch(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Make decisions for multiple candidates
        
        Args:
            candidates: List of dicts with market, news, options analysis
            
        Returns:
            List of decisions
        """
        decisions = []
        
        for candidate in candidates:
            symbol = candidate.get('symbol', 'UNKNOWN')
            market = candidate.get('market_analysis', {})
            news = candidate.get('news_analysis', {})
            options = candidate.get('options_analysis', {})
            
            decision = self.decide(symbol, market, news, options)
            decisions.append(decision)
        
        return decisions


# ============================================
# CLI / Standalone Usage
# ============================================

def load_latest_analyses():
    """Load the latest outputs from all agents"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    analyses = {}
    
    # Load Market Agent output
    market_dir = os.path.join(base_dir, "..", "Market Agent Output")
    market_files = glob.glob(os.path.join(market_dir, "*.json"))
    if market_files:
        latest = max(market_files, key=os.path.getctime)
        with open(latest, 'r') as f:
            data = json.load(f)
            analyses['market'] = {item['symbol']: item for item in data.get('analyses', [])}
    
    # Load News Agent output
    news_dir = os.path.join(base_dir, "..", "News Agent Output")
    news_files = glob.glob(os.path.join(news_dir, "*.json"))
    if news_files:
        latest = max(news_files, key=os.path.getctime)
        with open(latest, 'r') as f:
            data = json.load(f)
            analyses['news'] = {item['symbol']: item for item in data.get('news_analysis', [])}
    
    # Load Options Agent output
    options_dir = os.path.join(base_dir, "..", "Options Agent Output")
    options_files = glob.glob(os.path.join(options_dir, "*.json"))
    if options_files:
        latest = max(options_files, key=os.path.getctime)
        with open(latest, 'r') as f:
            data = json.load(f)
            analyses['options'] = {item['symbol']: item for item in data}
    
    return analyses


def main():
    """Main entry point for standalone testing"""
    print("🚀 Decision Agent - Alpaca AI Hackathon 2026")
    print("=" * 50)
    
    # Initialize agent
    portfolio = PortfolioState(
        account_equity=100000,
        cash=70000,
        buying_power=65000,
        open_positions=[],
        total_exposure=0,
        total_risk=0
    )
    
    risk_constraints = RiskConstraints(
        max_trade_allocation_pct=5.0,
        max_total_exposure_pct=20.0,
        max_account_risk_pct=1.0
    )
    
    agent = DecisionAgent(
        sandbox_mode=True,
        portfolio=portfolio,
        risk_constraints=risk_constraints
    )
    
    # Sample test data (matching your agents' outputs)
    test_candidate = {
        "symbol": "NVDA",
        "market_analysis": {
            "direction": "BULLISH",
            "confidence": 0.85,
            "reasoning": "Price above both SMAs with RSI showing strong momentum",
            "key_factors": ["Price > SMA20 > SMA50", "RSI > 60"]
        },
        "news_analysis": {
            "news_score": 84.5,
            "overall_sentiment": "positive",
            "overall_impact": "high",
            "relevant_news_count": 5,
            "catalysts": ["Raised revenue guidance", "New AI GPU announcement"],
            "risks": ["Increasing AI accelerator competition"],
            "events": []
        },
        "options_analysis": {
            "strategy_type": "BullCallSpread",
            "confidence": 0.89,
            "legs": [
                {"action": "BUY", "option_type": "CALL", "strike": 180.0, "expiration": "2026-09-15"},
                {"action": "SELL", "option_type": "CALL", "strike": 190.0, "expiration": "2026-09-15"}
            ],
            "estimated_max_loss": 240.0,
            "estimated_max_profit": 760.0,
            "risk_reward_ratio": 3.17,
            "reasoning": "Bullish spread with favorable R/R"
        }
    }
    
    print("\n📊 Testing Decision Agent on NVDA...")
    print(f"   Market: {test_candidate['market_analysis']['direction']} ({test_candidate['market_analysis']['confidence']:.2%})")
    print(f"   News: {test_candidate['news_analysis']['overall_sentiment']} (Score: {test_candidate['news_analysis']['news_score']:.1f})")
    print(f"   Options: {test_candidate['options_analysis']['strategy_type']} (R/R: {test_candidate['options_analysis']['risk_reward_ratio']:.2f})")
    
    # Make decision
    print("\n🤔 Making decision...")
    decision = agent.decide(
        test_candidate['symbol'],
        test_candidate['market_analysis'],
        test_candidate['news_analysis'],
        test_candidate['options_analysis']
    )
    
    # Display results
    print("\n📈 Decision Result:")
    print(f"   Symbol: {decision['symbol']}")
    print(f"   Decision: {decision['decision']}")
    print(f"   Confidence: {decision['confidence']:.2%}")
    print(f"   Reasoning: {decision['reasoning']}")
    
    if decision['decision'] == 'TRADE':
        print(f"   Strategy: {decision.get('strategy_type', 'Unknown')}")
        if decision.get('legs'):
            print("   Legs:")
            for leg in decision['legs']:
                print(f"     - {leg.get('action')} {leg.get('option_type')} @ ${leg.get('strike')}")
        if decision.get('risk_assessment'):
            ra = decision['risk_assessment']
            print(f"   Max Loss: ${ra.get('max_loss_per_contract', 0):.2f}")
            print(f"   Max Profit: ${ra.get('max_profit_per_contract', 0):.2f}")
            print(f"   R/R: {ra.get('risk_reward_ratio', 0):.2f}")
    
    # Save output
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Decision Agent Output")
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_dir, f"decision_{timestamp}.json")
    
    output_data = {
        "run_timestamp": timestamp,
        "portfolio_state": {
            "account_equity": portfolio.account_equity,
            "cash": portfolio.cash,
            "total_exposure": portfolio.total_exposure,
            "total_risk": portfolio.total_risk
        },
        "decision": decision
    }
    
    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n💾 Decision saved to {filename}")
    
    return decision


if __name__ == "__main__":
    import glob  # Added for file discovery
    main()