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
        
        import sys
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if base_dir not in sys.path:
            sys.path.append(base_dir)
            
        from shared_portfolio import calculate_portfolio_economics
        eco = calculate_portfolio_economics(positions_info)
            
        return {
            "equity": equity,
            "buying_power": buying_power,
            "start_of_day_equity": start_of_day_equity,
            "existing_capital_exposure": eco["total_exposure"],
            "open_positions_count": eco["open_positions_count"]
        }

    def evaluate_trade(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        symbol = proposal.get("symbol")
        strategy_obj = proposal.get("strategy", {})
        strategy_type = strategy_obj.get("type", "Unknown")

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

        # --- Phase 1: Strategy Quality Hard Constraints ---
        if max_loss_per_contract <= 0:
            checks["max_risk_per_trade"] = "FAIL"
            rejection_reasons.append("Invalid options structure (max loss <= 0).")
            return self._build_reject_response(symbol, strategy_type, checks, rejection_reasons)
            
        risk_reward_ratio = float('inf')
        if max_loss_per_contract > 0:
            risk_reward_ratio = round(max_profit_per_contract / max_loss_per_contract, 2)
            
        min_rr = self.config.get("min_risk_reward", 1.5)
        
        # Credit spreads naturally have max profit < max loss
        # Only enforce hard min_rr (1.5) on debit-oriented strategies
        debit_strategies = ["LongCall", "LongPut", "BullCallSpread", "BearPutSpread"]
        if strategy_type in debit_strategies:
            if risk_reward_ratio < min_rr:
                checks["risk_reward"] = "FAIL"
                rejection_reasons.append(f"Risk/Reward ratio {risk_reward_ratio} is below minimum {min_rr}.")
                return self._build_reject_response(symbol, strategy_type, checks, rejection_reasons)
            
        max_open_positions = self.config.get("max_open_positions", 999)
        if open_positions_count >= max_open_positions:
            checks["open_positions"] = "FAIL"
            rejection_reasons.append(f"Current open positions ({open_positions_count}) reached or exceeded limit of {max_open_positions}.")
            return self._build_reject_response(symbol, strategy_type, checks, rejection_reasons)
        open_position_capacity = max(0, max_open_positions - open_positions_count)

        # --- Phase 2: Calculate Capacities ---
        exposure_per_contract = max_loss_per_contract
        capital_required_per_contract = max_loss_per_contract

        # 2a. Risk-Based Capacity
        max_risk_pct = self.config.get("max_risk_per_trade_pct", 1.0)
        per_trade_risk_budget = equity * (max_risk_pct / 100.0)
        
        max_exposure_pct = self.config.get("max_exposure_pct", 100.0)
        max_portfolio_exposure_limit = equity * (max_exposure_pct / 100.0)
        available_exposure_budget = max(0.0, max_portfolio_exposure_limit - existing_capital_exposure)
        
        current_equity_drawdown = max(0.0, start_of_day_equity - equity)
        max_daily_loss_pct = self.config.get("max_daily_loss_pct", 100.0)
        max_daily_loss_limit = equity * (max_daily_loss_pct / 100.0)
        available_daily_loss_budget = max(0.0, max_daily_loss_limit - current_equity_drawdown)
        
        max_account_risk_pct = self.config.get("max_account_risk_pct", 5.0)
        max_account_risk_limit = equity * (max_account_risk_pct / 100.0)
        available_account_risk_budget = max(0.0, max_account_risk_limit - existing_capital_exposure)
        
        allowed_risk_without_buying_power = min(
            per_trade_risk_budget,
            available_exposure_budget,
            available_account_risk_budget,
            available_daily_loss_budget
        )
        risk_based_contracts = math.floor(allowed_risk_without_buying_power / max_loss_per_contract)
        
        # 2b. Buying Power Capacity
        buying_power_contracts = math.floor(buying_power / capital_required_per_contract)

        # 2c. Final Pre-Adjustment Capacity
        max_contracts_allowed = min(
            risk_based_contracts,
            buying_power_contracts,
            open_position_capacity
        )
        
        if max_contracts_allowed < 1:
            checks["max_risk_per_trade"] = "FAIL"
            bindings = []
            if per_trade_risk_budget < max_loss_per_contract: bindings.append("ALLOCATION")
            if available_exposure_budget < max_loss_per_contract: bindings.append("EXPOSURE")
            if available_account_risk_budget < max_loss_per_contract: bindings.append("RISK")
            if available_daily_loss_budget < max_loss_per_contract: bindings.append("DAILY_LOSS")
            if buying_power < capital_required_per_contract: bindings.append("BUYING_POWER")
            if open_position_capacity < 1: bindings.append("OPEN_POSITIONS")
            
            binding = ", ".join(bindings) if bindings else "UNKNOWN_CONSTRAINT"
            return self._build_reject_response(
                symbol, strategy_type, checks, 
                [f"NO_EXECUTABLE_CONTRACT_CAPACITY. Binding constraint: {binding} (0 contracts allowed)."]
            )
            
        approved_contracts = max_contracts_allowed

        # --- Phase 3: Post-Resize Verification ---
        new_trade_max_loss = max_loss_per_contract * approved_contracts
        new_trade_capital_requirement = new_trade_max_loss
        max_profit_total = max_profit_per_contract * approved_contracts
        
        res = {
            "decision": "ACCEPT",
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
                "contracts": approved_contracts,
                "limit_price": round(net_price, 2)
            }
        }
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
        decision_dir = os.path.join(base_dir, "SAVE-DATA-PER-AGENT", "Decision-Agent-Output")
        
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
                logger.info(f"Skipping {decision.get('symbol', 'UNKNOWN')} - Decision was REJECT.")
                continue
                
            symbol = decision.get("symbol")
            strategy = decision.get("strategy", {})
            
            proposal = {
                "symbol": symbol,
                "strategy": strategy
            }
            logger.info(f"Evaluating TRADE qualitative proposal for {symbol}")
            result = self.evaluate_trade(proposal)
            results.append(result)
            
            if result.get("decision") == "ACCEPT":
                logger.info(f"✅ {symbol} Risk Check: ACCEPT (Approved: {result.get('order', {}).get('contracts', 0)})")
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
        out_dir = os.path.join(base_dir, "SAVE-DATA-PER-AGENT", "Risk-Engine-Output")
        os.makedirs(out_dir, exist_ok=True)
        
        filename = f"risk_analysis_{data['run_timestamp']}.json"
        filepath = os.path.join(out_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"💾 Saved Risk Engine output to {filepath}")


def main():
    import sys
    print("🛡️ Risk Engine Execution Loop")
    print("=" * 40)
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "User_Config", "config.json")
    
    if not os.path.exists(config_path):
        logger.error(f"Config not found at {config_path}")
        sys.exit(1)
        
    try:
        with open(config_path, 'r') as f:
            config_data = json.load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        sys.exit(1)
        
    risk_config = config_data.get("risk_limits", {})
    
    # Initialize without mock TradingClient to use the live Alpaca config via .env
    evaluator = RiskEvaluator(risk_config)
    evaluator.process_decisions()

if __name__ == "__main__":
    main()
