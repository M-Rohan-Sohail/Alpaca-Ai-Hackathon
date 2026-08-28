#!/usr/bin/env python
"""
Decision Agent - Aggregates all agent outputs and makes final TRADE/PASS decision
Refactored to support LLM qualitative reasoning and strict Python quantitative validation.
"""

import os
import json
import glob
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from dataclasses import dataclass

from groq import Groq
from dotenv import load_dotenv, find_dotenv

# Optional Alpaca integration
try:
    from alpaca.trading.client import TradingClient
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IncompleteDataError(Exception):
    """Raised when one or more agent outputs are missing or invalid."""
    pass


@dataclass
class RiskConstraints:
    """Risk constraints from user config"""
    max_trade_allocation_pct: float = 5.0
    max_total_exposure_pct: float = 20.0
    max_account_risk_pct: float = 1.0


class DecisionAgent:
    """
    Decision Agent - Qualitatively analyzes using LLM, and validates quantitatively using raw Python.
    """
    
    def __init__(self,
                 api_key: Optional[str] = None,
                 model: str = "openai/gpt-oss-120b",
                 temperature: float = 0.2,
                 sandbox_mode: bool = False,
                 risk_constraints: Optional[RiskConstraints] = None):
        
        self.model = model
        self.temperature = temperature
        self.sandbox_mode = sandbox_mode
        self.risk_constraints = risk_constraints or RiskConstraints()
        
        load_dotenv(find_dotenv())
        
        self.alpaca_api_key = os.getenv("ALPACA_API_KEY", "")
        self.alpaca_secret_key = os.getenv("ALPACA_SECRET_KEY", "")
        self.alpaca_paper = os.getenv("ALPACA_PAPER", "True").lower() == "true"
        
        if not ALPACA_AVAILABLE or not self.alpaca_api_key or not self.alpaca_secret_key:
            raise ValueError("Alpaca API keys and SDK are required for the Decision Agent.")
        
        self.trading_client = TradingClient(self.alpaca_api_key, self.alpaca_secret_key, paper=self.alpaca_paper)
        logger.info("✅ Alpaca client initialized")
            
        api_key = api_key or os.getenv('GROQ_API_KEY')
        if not api_key:
            raise ValueError("GROQ_API_KEY is required for the Decision Agent.")
            
        try:
            self.client = Groq(api_key=api_key)
            logger.info("✅ Groq client initialized")
        except Exception as e:
            raise ValueError(f"Failed to initialize Groq: {e}")

    def _get_latest_json(self, folder_path: str) -> Optional[Any]:
        if not os.path.exists(folder_path):
            return None
        files = glob.glob(os.path.join(folder_path, "*.json"))
        if not files:
            return None
        latest_file = max(files, key=os.path.getctime)
        try:
            with open(latest_file, 'r') as f:
                data = json.load(f)
                return data
        except Exception as e:
            logger.error(f"Error reading {latest_file}: {e}")
            return None

    def _load_latest_agent_outputs(self, symbol: str) -> Tuple[Dict, Dict, Dict]:
        """Loads and extracts the latest data for the specific symbol from Market, News, Options agents."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        market_dir = os.path.join(base_dir, "Market Agent Output")
        news_dir = os.path.join(base_dir, "News Agent Output")
        options_dir = os.path.join(base_dir, "Options Agent Output")

        market_data = self._get_latest_json(market_dir)
        news_data = self._get_latest_json(news_dir)
        options_data = self._get_latest_json(options_dir)

        if not market_data or not news_data or not options_data:
            raise IncompleteDataError("Missing one or more agent output JSON files.")
        
        # Parse Market Data (assumed format: {"analyses": [ {symbol...} ]})
        if isinstance(market_data, dict) and "analyses" in market_data:
            m_cand = next((c for c in market_data["analyses"] if c.get('symbol') == symbol), None)
        else:
            m_cand = next((c for c in market_data if c.get('symbol') == symbol), None) if isinstance(market_data, list) else None

        # Parse News Data (assumed format: [ {symbol...} ] or {"news_analysis": [...]})
        if isinstance(news_data, dict) and "news_analysis" in news_data:
             n_cand = next((c for c in news_data["news_analysis"] if c.get('symbol') == symbol), None)
        elif isinstance(news_data, dict) and "analyses" in news_data:
             n_cand = next((c for c in news_data["analyses"] if c.get('symbol') == symbol), None)
        elif isinstance(news_data, list):
             n_cand = next((c for c in news_data if c.get('symbol') == symbol), None)
        else:
            n_cand = None
            
        # Parse Options Data
        if isinstance(options_data, dict) and "candidates" in options_data:
             o_cand = next((c for c in options_data["candidates"] if c.get('symbol') == symbol), None)
        elif isinstance(options_data, list):
             o_cand = next((c for c in options_data if c.get('symbol') == symbol), None)
        else:
            o_cand = None

        if not m_cand or not n_cand or not o_cand:
            raise IncompleteDataError(f"Data for {symbol} not found across all 3 agent outputs.")

        if m_cand.get('error') or m_cand.get('direction') == 'NEUTRAL' and m_cand.get('confidence') == 0.0:
            raise IncompleteDataError(f"Market agent contains an error/invalid output for {symbol}.")
            
        return m_cand, n_cand, o_cand

    def _fetch_portfolio_data(self) -> Dict:
        """Fetch real Portfolio Data using Alpaca SDK."""
        if not self.trading_client:
            raise RuntimeError("TradingClient is not initialized.")
        
        try:
            account = self.trading_client.get_account()
            positions = self.trading_client.get_all_positions()
            
            equity = float(account.equity)
            cash = float(account.cash)
            buying_power = float(account.buying_power)
            
            total_exposure = sum([abs(float(p.market_value)) for p in positions])
            total_risk = sum([abs(float(p.cost_basis)) for p in positions]) 
            
            return {
                "account_equity": equity,
                "cash": cash,
                "buying_power": buying_power,
                "existing_positions": [{"symbol": p.symbol, "market_value": str(p.market_value)} for p in positions],
                "total_exposure": total_exposure,
                "total_risk": total_risk
            }
        except Exception as e:
            logger.error(f"Error fetching portfolio data from Alpaca: {e}")
            raise

    def _calculate_metrics(self, legs: List[Dict]) -> Dict:
        """
        Determines Max Profit, Max Loss, Net Cost, and Breakeven for Single Leg and Vertical Spreads.
        Multiplier is strictly 100 per contract.
        """
        if not legs:
            raise ValueError("No option legs provided")

        cost_per_share = 0.0
        for leg in legs:
            multiplier = 1 if leg.get('action', '').upper() == 'BUY' else -1
            cost_per_share += multiplier * leg.get('price', 0.0)
            
        net_cost = cost_per_share # positive = debit, negative = credit

        if len(legs) == 1:
            leg = legs[0]
            action = leg.get('action', '').upper()
            op_type = leg.get('option_type', '').upper()
            strike = leg.get('strike', 0.0)
            price = leg.get('price', 0.0)

            if action == 'BUY':
                max_loss = price
                max_profit = float('inf')
                breakeven = strike + price if op_type == 'CALL' else strike - price
            else:
                max_profit = price
                max_loss = float('inf')
                breakeven = strike + price if op_type == 'CALL' else strike - price
                
        elif len(legs) == 2:
            # Sort by strike for consistent vertical spread logic
            legs = sorted(legs, key=lambda x: x.get('strike', 0.0))
            leg1 = legs[0]
            leg2 = legs[1]
            strike_width = leg2.get('strike', 0.0) - leg1.get('strike', 0.0)
            
            op_type1 = leg1.get('option_type', '').upper()
            op_type2 = leg2.get('option_type', '').upper()
            
            if op_type1 == op_type2:
                # Vertical spread
                if net_cost > 0: # Debit spread
                    max_loss = net_cost
                    max_profit = strike_width - net_cost
                    if op_type1 == 'CALL': # Bull Call
                        breakeven = leg1.get('strike', 0.0) + net_cost
                    else: # Bear Put
                        breakeven = leg2.get('strike', 0.0) - net_cost
                else: # Credit spread
                    max_profit = abs(net_cost)
                    max_loss = strike_width - max_profit
                    if op_type1 == 'CALL': # Bear Call
                        breakeven = leg1.get('strike', 0.0) + max_profit
                    else: # Bull Put
                        breakeven = leg2.get('strike', 0.0) - max_profit
            else:
                raise ValueError("Unsupported 2-leg strategy (types differ)")
        else:
            raise ValueError("Unsupported strategy structure: too many legs")

        return {
            "net_cost": net_cost * 100,
            "max_loss": max_loss * 100,
            "max_profit": max_profit * 100 if max_profit != float('inf') else max_profit,
            "breakeven": breakeven,
            "risk_reward_ratio": (max_profit / max_loss) if max_loss > 0 and max_loss != float('inf') else float('inf')
        }

    def _get_llm_decision(self, symbol: str, m_cand: Dict, n_cand: Dict, o_cand: Dict, portfolio: Dict) -> Dict:
        """Step 1: LLM Qualitative Reasoning"""
        prompt = f"""
You are a senior portfolio manager. Evaluate the following data and make a qualitative decision (TRADE or PASS).
Check directional alignment between Market, News, and Options strategies. Consider existing portfolio context.

Candidate: {symbol}

MARKET AGENT:
{json.dumps(m_cand, indent=2)}

NEWS AGENT:
{json.dumps(n_cand, indent=2)}

OPTIONS AGENT:
{json.dumps(o_cand, indent=2)}

PORTFOLIO:
{json.dumps(portfolio, indent=2)}

RISK CONSTRAINTS:
{json.dumps(self.risk_constraints.__dict__, indent=2)}

Make a qualitative decision. Output strictly in JSON format matching this structure exactly:
{{
  "symbol": "{symbol}",
  "decision": "TRADE", 
  "direction": "BULLISH", 
  "strategy": {{
    "type": "BullCallSpread", 
    "legs": [
      {{ "symbol": "AAPL260915C00180000", "action": "BUY", "option_type": "CALL", "strike": 180.0, "expiration": "2026-09-15", "price": 3.60 }}
    ]
  }},
  "confidence": 0.90, 
  "reasoning": "Explain why..."
}}
"""
        if self.sandbox_mode:
            logger.warning("Sandbox mode is deprecated. Running in live mode.")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            return {"symbol": symbol, "decision": "PASS", "reasoning": f"LLM error: {e}", "confidence": 0.0}

    def _validate_and_resize_trade(self, llm_decision: Dict, portfolio: Dict) -> Dict:
        """Step 2: Python Quantitative Validation & Risk Enforcement"""
        if llm_decision.get('decision') != 'TRADE':
            return {
                "symbol": llm_decision.get("symbol"),
                "decision": "PASS",
                "reasoning": llm_decision.get("reasoning", "LLM decided to pass."),
                "confidence": llm_decision.get("confidence", 0.0)
            }
            
        strategy = llm_decision.get('strategy', {})
        legs = strategy.get('legs', [])
        
        try:
            metrics = self._calculate_metrics(legs)
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return {
                "symbol": llm_decision.get("symbol"),
                "decision": "PASS",
                "reasoning": f"Rejected by Risk Engine: {str(e)}",
                "confidence": 0.0
            }

        max_loss_per_contract = metrics['max_loss']
        if max_loss_per_contract == float('inf'):
            logger.warning("Trade rejected: Strategy involves unlimited risk.")
            return {
                "symbol": llm_decision.get("symbol"),
                "decision": "PASS",
                "reasoning": "Rejected by Risk Engine: Strategy has unlimited max loss.",
                "confidence": 0.0
            }

        account_equity = portfolio['account_equity']
        
        max_trade_cap = account_equity * (self.risk_constraints.max_trade_allocation_pct / 100.0)
        max_total_exposure = account_equity * (self.risk_constraints.max_total_exposure_pct / 100.0)
        max_account_risk = account_equity * (self.risk_constraints.max_account_risk_pct / 100.0)
        
        if max_loss_per_contract <= 0:
            # Prevent zero division or illogical scenarios
            max_contracts = 0 
        else:
            c1 = max_trade_cap // max_loss_per_contract
            avail_exposure = max(0, max_total_exposure - portfolio['total_exposure'])
            c2 = avail_exposure // max_loss_per_contract
            avail_risk = max(0, max_account_risk - portfolio['total_risk'])
            c3 = avail_risk // max_loss_per_contract
            
            max_contracts = int(min(c1, c2, c3))
        
        if max_contracts <= 0:
            return {
                "symbol": llm_decision.get("symbol"),
                "decision": "PASS",
                "reasoning": "Rejected by Risk Engine: Risk limits exceeded (would require < 1 contract).",
                "confidence": 0.0,
                "risk_assessment": {
                    "status": "REJECTED",
                    "max_loss_per_contract": max_loss_per_contract
                }
            }
            
        return {
            "symbol": llm_decision.get("symbol"),
            "decision": "TRADE",
            "direction": llm_decision.get("direction", ""),
            "strategy": strategy,
            "confidence": llm_decision.get("confidence", 0.0),
            "reasoning": llm_decision.get("reasoning", ""),
            "risk_assessment": {
                "status": "ACCEPTABLE",
                "approved_contracts": max_contracts,
                "max_loss_per_contract": metrics['max_loss'],
                "max_profit_per_contract": metrics['max_profit'] if metrics['max_profit'] != float('inf') else "Unlimited",
                "risk_reward_ratio": metrics['risk_reward_ratio'],
                "breakeven": metrics['breakeven']
            }
        }

    def decide(self, symbols: List[str]) -> Dict:
        """Main orchestrator for making decisions on a list of symbols"""
        logger.info(f"🤔 DecisionAgent starting run for symbols: {symbols}")
        
        try:
            portfolio = self._fetch_portfolio_data()
        except Exception as e:
            logger.error("Failed to fetch portfolio data. Aborting.")
            return {"error": "Portfolio data fetch failed"}

        results = []
        for symbol in symbols:
            logger.info(f"--- Analyzing {symbol} ---")
            try:
                m_cand, n_cand, o_cand = self._load_latest_agent_outputs(symbol)
                llm_decision = self._get_llm_decision(symbol, m_cand, n_cand, o_cand, portfolio)
                final_decision = self._validate_and_resize_trade(llm_decision, portfolio)
                results.append(final_decision)
                
                if final_decision.get('decision') == 'TRADE':
                    logger.info(f"✅ {symbol}: TRADE approved for {final_decision.get('risk_assessment', {}).get('approved_contracts', 0)} contracts.")
                else:
                    logger.info(f"❌ {symbol}: PASS - {final_decision.get('reasoning')}")

            except IncompleteDataError as e:
                logger.error(f"❌ Incomplete Data for {symbol}: {e}")
                results.append({
                    "symbol": symbol,
                    "decision": "PASS",
                    "reasoning": f"Incomplete Data: {e}"
                })
            except Exception as e:
                logger.error(f"❌ Unexpected error processing {symbol}: {e}")
                results.append({
                    "symbol": symbol,
                    "decision": "PASS",
                    "reasoning": f"Unexpected error: {e}"
                })

        output = {
            "run_timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "decisions": results
        }
        
        self._save_output(output)
        return output

    def _save_output(self, data: Dict):
        """Save the final decisions to the Decision Agent Output directory"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        out_dir = os.path.join(base_dir, "Decision Agent Output")
        os.makedirs(out_dir, exist_ok=True)
        
        filename = f"decision_analysis_{data['run_timestamp']}.json"
        filepath = os.path.join(out_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"💾 Saved Decision Agent output to {filepath}")


def main():
    print("🚀 Decision Agent Test")
    print("=" * 40)
    
    agent = DecisionAgent(sandbox_mode=False)
    
    # Ideally, get the candidates from a common scanner output.
    # For this test script, we assume the usual suspects.
    candidates = ["NVDA", "AAPL", "MSFT"]
    agent.decide(candidates)


if __name__ == "__main__":
    main()