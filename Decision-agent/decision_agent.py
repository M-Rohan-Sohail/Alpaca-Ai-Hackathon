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
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv

# Optional Alpaca integration
try:
    from alpaca.trading.client import TradingClient
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False


STRATEGY_BIAS = {
    "LongCall": "BULLISH",
    "BullCallSpread": "BULLISH",
    "BullPutSpread": "BULLISH",
    "LongPut": "BEARISH",
    "BearPutSpread": "BEARISH",
    "BearCallSpread": "BEARISH"
}


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IncompleteDataError(Exception):
    """Raised when one or more agent outputs are missing or invalid."""
    pass


# Removed RiskConstraints since Risk Engine handles quantitative risk


class DecisionAgent:
    """
    Decision Agent - Qualitatively analyzes using LLM, and validates quantitatively using raw Python.
    """
    
    def __init__(self,
                 api_key: Optional[str] = None,
                 model: str = "deepseek-ai/DeepSeek-V4-Flash-0731",
                 temperature: float = 0.2,
                 sandbox_mode: bool = False):
        
        self.model = model
        self.temperature = temperature
        self.sandbox_mode = sandbox_mode
        
        load_dotenv(find_dotenv())
        
        self.alpaca_api_key = os.getenv("ALPACA_API_KEY", "")
        self.alpaca_secret_key = os.getenv("ALPACA_SECRET_KEY", "")
        self.alpaca_paper = os.getenv("ALPACA_PAPER", "True").lower() == "true"
        
        if not ALPACA_AVAILABLE or not self.alpaca_api_key or not self.alpaca_secret_key:
            raise ValueError("Alpaca API keys and SDK are required for the Decision Agent.")
        
        self.trading_client = TradingClient(self.alpaca_api_key, self.alpaca_secret_key, paper=self.alpaca_paper)
        logger.info("✅ Alpaca client initialized")
            
        api_key = api_key or os.getenv('FEATHERLESS_API_KEY')
        if not api_key:
            raise ValueError("FEATHERLESS_API_KEY is required for the Decision Agent.")
            
        try:
            self.client = OpenAI(api_key=api_key, base_url="https://api.featherless.ai/v1")
            logger.info("✅ LLM client initialized")
        except Exception as e:
            raise ValueError(f"Failed to initialize LLM client: {e}")

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
        
        market_dir = os.path.join(base_dir, "SAVE-DATA-PER-AGENT", "Market-Agent-Output")
        news_dir = os.path.join(base_dir, "SAVE-DATA-PER-AGENT", "News-Agent-Output")
        options_dir = os.path.join(base_dir, "SAVE-DATA-PER-AGENT", "Options-Agent-Output")

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
            
            # Use the authoritative shared portfolio economics module
            import sys
            import os
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if base_dir not in sys.path:
                sys.path.append(base_dir)
                
            from shared_portfolio import calculate_portfolio_economics
            eco = calculate_portfolio_economics(positions)
            
            return {
                "account_equity": equity,
                "cash": cash,
                "buying_power": buying_power,
                "existing_positions": [{"symbol": p.symbol, "market_value": str(p.market_value)} for p in positions],
                "total_exposure": eco["total_exposure"],
                "total_risk": eco["total_risk"],
                "open_positions_count": eco["open_positions_count"]
            }
        except Exception as e:
            logger.error(f"Error fetching portfolio data from Alpaca: {e}")
            raise

    # Removed _calculate_metrics since Risk Engine is the quantitative authority

    def _get_llm_decision(self, symbol: str, m_cand: Dict, n_cand: Dict, o_cand: Dict, portfolio: Dict) -> Dict:
        """Step 1: LLM Qualitative Reasoning"""
        prompt = f"""
You are a senior portfolio manager making a qualitative final decision: TRADE or REJECT.

Your role is to evaluate whether the proposed trade forms a coherent and executable investment thesis based on the outputs of the Market Agent, News Agent, and Options Agent.

AGENT ROLES:

* Market Agent: Primary directional thesis. It answers:
  "What is the underlying currently doing?"
  The Market Agent is the primary source for the underlying's directional bias.

* News Agent: Confirmation, catalyst, or risk modifier. It answers:
  "Does current news support, weaken, or contradict the market thesis?"
  News disagreement is not automatically a reason to reject a trade.

* Options Agent: Strategy implementation. It answers:
  "Given the Market Agent's thesis and the available option chain, what options structure is the most appropriate way to express that thesis?"
  The Options Agent should not be treated as an independent source of the underlying's directional thesis.

* You (Decision LLM): Final qualitative reasoning layer. You answer:
  "Does the proposed options trade logically express the market thesis, and is there a sufficient qualitative basis to proceed?"

IMPORTANT INSTRUCTION:
DO NOT CALCULATE NUMBERS.

Do not calculate or recalculate:

* Maximum loss
* Maximum profit
* Risk/reward ratio
* Number of contracts
* Position size
* Buying power
* Portfolio exposure
* Account risk

These values are calculated by deterministic components and/or the Risk Engine. Use the provided results as authoritative inputs.

DECISION PROCESS:

1. MARKET THESIS
   Evaluate the Market Agent's direction and confidence.

The Market Agent provides the primary underlying directional thesis:

* BULLISH
* BEARISH
* NEUTRAL

Do not override the Market Agent's direction based solely on the Options Agent's opinion.

2. NEWS ALIGNMENT
   Determine whether the News Agent:

* Supports the market thesis
* Is neutral
* Contradicts the market thesis

News disagreement is a risk modifier, not an automatic rejection.

Reject based on news only when the provided news indicates a material development that substantially undermines the proposed trade thesis.

3. OPTIONS STRATEGY ALIGNMENT
   Directional alignment has already been verified by the Python validation layer. Do not independently recalculate or override that validation. Evaluate whether the proposed structure qualitatively makes sense given the already-validated market thesis and the available options information.

If the Options Agent returns NO_VALID_STRUCTURE, REJECT the trade because there is no suitable options implementation of the market thesis.

4. CONFLICT RESOLUTION
   Do not treat every disagreement between agents as a hard conflict.

Use the following hierarchy:

* Market Agent = primary directional thesis
* News Agent = confirmation / risk modifier
* Options Agent = implementation of the market thesis
* Risk Engine = final authority on quantitative risk constraints

Do not reject a trade simply because News and Market signals are not perfectly aligned.

5. STRATEGY SUITABILITY
   Evaluate qualitatively whether the proposed strategy is appropriate for the market thesis and the available options data.

Consider:

* Directional consistency
* Quality of the proposed structure
* Whether the strategy is defined-risk
* Whether the strategy reasonably expresses the market thesis
* Whether the available option data supports the proposed structure

Do not override deterministic option filters or Risk Engine results.

6. QUALITATIVE PORTFOLIO CONSIDERATIONS
   Consider the overall quality and coherence of the opportunity based on the provided information.

Avoid introducing assumptions or information that is not provided.

FINAL DECISION:

Return TRADE only when:

* The market thesis provides a reasonable directional basis,
* There is no material qualitative contradiction that invalidates the thesis,
* The proposed strategy is qualitatively suitable,
* And all provided deterministic/risk checks have passed.

Otherwise return REJECT.

The Risk Engine is authoritative for quantitative risk constraints. If the Risk Engine returns REJECT, the final decision must be REJECT regardless of the qualitative assessment.

Do not invent missing information.
Do not speculate beyond the provided data.
Do not override deterministic validation results.

Evaluate the following data for {symbol}:

MARKET AGENT:
{json.dumps(m_cand, indent=2)}

NEWS AGENT:
{json.dumps(n_cand, indent=2)}

OPTIONS AGENT:
{json.dumps(o_cand, indent=2)}

PORTFOLIO:
{json.dumps(portfolio, indent=2)}

Output strictly in JSON format matching this structure exactly:
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
            return {"symbol": symbol, "decision": "REJECT", "reasoning": f"LLM error: {e}", "confidence": 0.0}

    # Removed _validate_and_resize_trade since Risk Engine is the quantitative authority

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
                
                # The LLM outputs qualitative data ONLY. We append it exactly as received.
                results.append(llm_decision)
                
                if llm_decision.get('decision') == 'TRADE':
                    logger.info(f"✅ {symbol}: TRADE qualitatively approved by LLM. Passing to Risk Engine.")
                else:
                    logger.info(f"❌ {symbol}: REJECT - {llm_decision.get('reasoning')}")

            except IncompleteDataError as e:
                logger.error(f"❌ Incomplete Data for {symbol}: {e}")
                results.append({
                    "symbol": symbol,
                    "decision": "REJECT",
                    "reasoning": f"Incomplete Data: {e}"
                })
            except Exception as e:
                logger.error(f"❌ Unexpected error processing {symbol}: {e}")
                results.append({
                    "symbol": symbol,
                    "decision": "REJECT",
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
        out_dir = os.path.join(base_dir, "SAVE-DATA-PER-AGENT", "Decision-Agent-Output")
        os.makedirs(out_dir, exist_ok=True)
        
        filename = f"decision_analysis_{data['run_timestamp']}.json"
        filepath = os.path.join(out_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"💾 Saved Decision Agent output to {filepath}")


def get_latest_json_file(directory: str):
    import glob
    import os
    if not os.path.exists(directory):
        return None
    json_files = glob.glob(os.path.join(directory, "*.json"))
    if not json_files:
        return None
    latest_file = max(json_files, key=os.path.getctime)
    return latest_file

def main():
    import json
    print("🚀 Decision Agent Live Run")
    print("=" * 40)
    
    agent = DecisionAgent(sandbox_mode=False)
    
    # Dynamically pull the candidates from the latest Deterministic Filter output
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    filter_dir = os.path.join(base_dir, "SAVE-DATA-PER-AGENT", "Deterministic-Filter-Output")
    latest_file = get_latest_json_file(filter_dir)
    
    if not latest_file:
        print(f"❌ No Deterministic Filter output found in {filter_dir}")
        return
        
    try:
        with open(latest_file, 'r') as f:
            data = json.load(f)
            
        candidates = []
        if "overall_ranking" in data and "candidates" in data["overall_ranking"]:
            candidates = [c["symbol"] for c in data["overall_ranking"]["candidates"]]
        elif "candidates" in data:
            candidates = [c["symbol"] for c in data["candidates"]]
            
        if not candidates:
            print("❌ No candidates found in the Deterministic Filter output.")
            return
            
        print(f"📊 Running Decision Agent for dynamic candidates: {candidates}")
        agent.decide(candidates)
        
    except Exception as e:
        print(f"❌ Error loading candidates: {e}")


if __name__ == "__main__":
    main()