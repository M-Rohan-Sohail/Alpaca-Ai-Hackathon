import math
import json
import os
import glob
import logging
from datetime import datetime
from typing import Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import Alpaca TradingClient, fallback gracefully if not installed for testing purposes
try:
    from alpaca.trading.client import TradingClient
except ImportError:
    TradingClient = Any

class RiskEvaluator:
    def __init__(self, config: Dict[str, Any], trading_client: TradingClient = None):
        self.config = config
        self.trading_client = trading_client
        
        # Initialize TradingClient if not provided and not a mock
        if self.trading_client is None:
            try:
                from dotenv import load_dotenv, find_dotenv
                load_dotenv(find_dotenv())
            except ImportError:
                pass
            api_key = os.getenv("ALPACA_API_KEY")
            api_secret = os.getenv("ALPACA_SECRET_KEY")
            if api_key and api_secret:
                self.trading_client = TradingClient(api_key, api_secret, paper=True)

    def _fetch_account_state(self) -> Dict[str, Any]:
        """Fetches the active account state directly from Alpaca."""
        if not self.trading_client:
            raise ValueError("TradingClient is not initialized.")
            
        account_info = self.trading_client.get_account()
        positions_info = self.trading_client.get_all_positions()
        
        equity = float(account_info.equity)
        buying_power = float(account_info.buying_power)
        start_of_day_equity = float(account_info.last_equity)
        
        # Calculate existing portfolio capital exposure (capital committed to open positions)
        existing_capital_exposure = 0.0
        for pos in positions_info:
            existing_capital_exposure += abs(float(pos.cost_basis))
            
        return {
            "equity": equity,
            "buying_power": buying_power,
            "start_of_day_equity": start_of_day_equity,
            "existing_capital_exposure": existing_capital_exposure,
            "open_positions_count": len(positions_info)
        }

    def evaluate_trade(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        symbol = proposal.get("symbol")
        strategy_obj = proposal.get("strategy", {})
        strategy_type = strategy_obj.get("type", "Unknown")
        proposed_contracts = proposal.get("proposed_contracts", 0)

        metrics = self._calc_strategy_metrics(strategy_obj)
        if not metrics:
            return self._build_reject_response(
                symbol, strategy_type, 
                {"max_risk_per_trade": "FAIL", "risk_reward": "FAIL", "portfolio_exposure": "FAIL", "buying_power": "FAIL", "open_positions": "FAIL", "daily_loss_limit": "FAIL"}, 
                ["Unsupported strategy type or invalid legs."]
            )

        max_loss_per_contract = metrics["max_loss_per_contract"]
        max_profit_per_contract = metrics["max_profit_per_contract"]
        breakeven = metrics["breakeven"]
        net_price = metrics["net_price"]

        # Fetch state dynamically
        try:
            account_state = self._fetch_account_state()
        except Exception as e:
            return self._build_reject_response(symbol, strategy_type, {}, [f"Failed to fetch account state: {str(e)}"])

        equity = account_state["equity"]
        start_of_day_equity = account_state["start_of_day_equity"]
        buying_power = account_state["buying_power"]
        existing_capital_exposure = account_state["existing_capital_exposure"]
        open_positions_count = account_state["open_positions_count"]

        rejection_reasons = []
        adjustments = []
        checks = {
            "max_risk_per_trade": "PASS",
            "risk_reward": "PASS",
            "portfolio_exposure": "PASS",
            "buying_power": "PASS",
            "open_positions": "PASS",
            "daily_loss_limit": "PASS"
        }

        # --- Rule 1. Max Trade Risk (and Sizing) ---
        max_risk_pct = self.config.get("max_risk_per_trade_pct", 1.0)
        max_allowed_risk = equity * (max_risk_pct / 100.0)

        adjusted_contracts = proposed_contracts
        if max_loss_per_contract > 0:
            max_contracts_allowed = math.floor(max_allowed_risk / max_loss_per_contract)
            if max_contracts_allowed == 0:
                checks["max_risk_per_trade"] = "FAIL"
                rejection_reasons.append(f"Maximum allowed risk is ${max_allowed_risk:.2f} but risk per contract is ${max_loss_per_contract:.2f}. Cannot trade even 1 contract.")
                adjusted_contracts = 0
            elif proposed_contracts > max_contracts_allowed:
                adjusted_contracts = max_contracts_allowed
                adjustments.append(f"Position size reduced from {proposed_contracts} to {adjusted_contracts} contracts to comply with maximum risk.")
        
        contracts_to_eval = adjusted_contracts if adjusted_contracts > 0 else proposed_contracts

        new_trade_max_loss = max_loss_per_contract * contracts_to_eval
        new_trade_capital_requirement = new_trade_max_loss  # For defined risk trades, requirement is usually max loss
        max_profit_total = max_profit_per_contract * contracts_to_eval

        # --- Rule 2. Portfolio Exposure ---
        projected_portfolio_exposure = existing_capital_exposure + new_trade_capital_requirement
        max_exposure_pct = self.config.get("max_exposure_pct", 100.0)
        max_portfolio_exposure_limit = equity * (max_exposure_pct / 100.0)

        if projected_portfolio_exposure > max_portfolio_exposure_limit:
            checks["portfolio_exposure"] = "FAIL"
            rejection_reasons.append(f"Projected portfolio capital exposure ${projected_portfolio_exposure:.2f} exceeds limit of ${max_portfolio_exposure_limit:.2f}.")

        # --- Rule 3. Daily Loss ---
        current_equity_drawdown = max(0, start_of_day_equity - equity)
        projected_daily_loss = current_equity_drawdown + new_trade_max_loss
        max_daily_loss_pct = self.config.get("max_daily_loss_pct", 100.0)
        max_daily_loss_limit = equity * (max_daily_loss_pct / 100.0)

        if projected_daily_loss > max_daily_loss_limit:
            checks["daily_loss_limit"] = "FAIL"
            rejection_reasons.append(f"Projected daily loss ${projected_daily_loss:.2f} exceeds limit of ${max_daily_loss_limit:.2f}.")

        # --- Rule 4. Buying Power ---
        if new_trade_capital_requirement > buying_power:
            checks["buying_power"] = "FAIL"
            rejection_reasons.append(f"Required capital ${new_trade_capital_requirement:.2f} exceeds available buying power ${buying_power:.2f}.")

        # --- Additional Check: Risk/Reward ---
        risk_reward_ratio = 0.0
        if new_trade_max_loss > 0:
            risk_reward_ratio = round(max_profit_total / new_trade_max_loss, 2)
        elif max_profit_total > 0:
            risk_reward_ratio = float('inf')

        min_rr = self.config.get("min_risk_reward", 1.5)
        if risk_reward_ratio < min_rr:
            checks["risk_reward"] = "FAIL"
            rejection_reasons.append(f"Risk/Reward ratio {risk_reward_ratio} is below minimum {min_rr}.")

        # --- Additional Check: Open Positions Limit ---
        max_open_positions = self.config.get("max_open_positions", 999)
        if (open_positions_count + 1) > max_open_positions:
            checks["open_positions"] = "FAIL"
            rejection_reasons.append(f"Projected open positions exceed limit of {max_open_positions}.")

        # Final evaluation
        if rejection_reasons or adjusted_contracts == 0:
            return self._build_reject_response(symbol, strategy_type, checks, rejection_reasons)

        res = {
            "decision": "PASS",
            "symbol": symbol,
            "strategy": strategy_type,
            "risk": {
                "max_loss_per_contract": round(max_loss_per_contract, 2),
                "max_loss_total": round(new_trade_max_loss, 2),
                "max_profit_per_contract": round(max_profit_per_contract, 2) if max_profit_per_contract != float('inf') else "Unlimited",
                "max_profit_total": round(max_profit_total, 2) if max_profit_total != float('inf') else "Unlimited",
                "risk_reward_ratio": risk_reward_ratio,
                "breakeven": round(breakeven, 2)
            },
            "checks": checks,
            "order": {
                "contracts": adjusted_contracts,
                "limit_price": round(net_price, 2)
            }
        }
        if adjustments:
            res["adjustments"] = adjustments

        return res

    def _calc_strategy_metrics(self, strategy: Dict[str, Any]) -> Dict[str, float]:
        legs = strategy.get("legs", [])
        if not legs:
            return {}

        cost_per_share = 0.0
        for leg in legs:
            multiplier = 1 if leg.get('action', '').upper() == 'BUY' else -1
            cost_per_share += multiplier * leg.get('price', 0.0)

        net_cost = cost_per_share

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
                return {} # We don't support naked selling
                
        elif len(legs) == 2:
            legs = sorted(legs, key=lambda x: x.get('strike', 0.0))
            leg1 = legs[0]
            leg2 = legs[1]
            strike_width = leg2.get('strike', 0.0) - leg1.get('strike', 0.0)
            
            op_type1 = leg1.get('option_type', '').upper()
            op_type2 = leg2.get('option_type', '').upper()
            
            if op_type1 == op_type2:
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
                return {}
        else:
            return {}

        return {
            "max_loss_per_contract": max_loss * 100,
            "max_profit_per_contract": max_profit * 100 if max_profit != float('inf') else float('inf'),
            "breakeven": breakeven,
            "net_price": net_cost
        }

    def _build_reject_response(self, symbol: str, strategy_type: str, checks: Dict[str, str], reasons: list) -> Dict[str, Any]:
        return {
            "decision": "REJECT",
            "symbol": symbol,
            "strategy": strategy_type,
            "checks": checks,
            "rejection_reasons": reasons
        }

    def process_decisions(self):
        """Polls the Decision Agent Output directory, parses TRADE decisions, evaluates them, and saves results."""
        logger.info("🛡️ Risk Assessment Engine starting run...")
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        decision_dir = os.path.join(base_dir, "Decision Agent Output")
        
        if not os.path.exists(decision_dir):
            logger.error(f"Directory not found: {decision_dir}")
            return
            
        files = glob.glob(os.path.join(decision_dir, "*.json"))
        if not files:
            logger.info("No Decision Agent outputs found.")
            return
            
        latest_file = max(files, key=os.path.getctime)
        logger.info(f"Loading latest decision file: {os.path.basename(latest_file)}")
        
        try:
            with open(latest_file, 'r') as f:
                decision_data = json.load(f)
        except Exception as e:
            logger.error(f"Error reading {latest_file}: {e}")
            return
            
        decisions = decision_data.get("decisions", [])
        results = []
        
        for decision in decisions:
            if decision.get("decision") != "TRADE":
                logger.info(f"Skipping {decision.get('symbol', 'UNKNOWN')} - Decision was PASS.")
                continue
                
            symbol = decision.get("symbol")
            strategy = decision.get("strategy", {})
            
            # The decision agent outputs approved_contracts inside risk_assessment
            risk_assessment = decision.get("risk_assessment", {})
            proposed_contracts = risk_assessment.get("approved_contracts", 0)
            
            proposal = {
                "symbol": symbol,
                "strategy": strategy,
                "proposed_contracts": proposed_contracts
            }
            
            logger.info(f"Evaluating TRADE proposal for {symbol} ({proposed_contracts} contracts)")
            result = self.evaluate_trade(proposal)
            results.append(result)
            
            if result.get("decision") == "PASS":
                logger.info(f"✅ {symbol} Risk Check: PASS (Approved: {result.get('order', {}).get('contracts', 0)})")
            else:
                logger.warning(f"❌ {symbol} Risk Check: REJECT ({result.get('rejection_reasons', ['Unknown error'])})")
                
        output = {
            "run_timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "source_file": os.path.basename(latest_file),
            "evaluations": results
        }
        
        self._save_output(output, base_dir)
        return output
        
    def _save_output(self, data: Dict, base_dir: str):
        out_dir = os.path.join(base_dir, "Risk Engine Output")
        os.makedirs(out_dir, exist_ok=True)
        
        filename = f"risk_analysis_{data['run_timestamp']}.json"
        filepath = os.path.join(out_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"💾 Saved Risk Engine output to {filepath}")


def main():
    print("🛡️ Risk Engine Execution Loop")
    print("=" * 40)
    
    config = {
        "max_risk_per_trade_pct": 1.0,
        "max_daily_loss_pct": 3.0,
        "max_open_positions": 5,
        "max_exposure_pct": 20.0,
        "min_risk_reward": 1.5,
        "max_holding_days": 10
    }
    
    # Initialize without mock TradingClient to use the live Alpaca config via .env
    evaluator = RiskEvaluator(config)
    evaluator.process_decisions()

if __name__ == "__main__":
    main()
