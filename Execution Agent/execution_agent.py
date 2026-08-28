import os
import json
import glob
import logging
from datetime import datetime
from dotenv import load_dotenv, find_dotenv

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest, OptionLegRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass, PositionIntent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RISK_OUT_DIR = os.path.join(BASE_DIR, "SAVE-DATA-PER-AGENT", "Risk-Engine-Output")
DECISION_OUT_DIR = os.path.join(BASE_DIR, "Decision Agent Output")
EXECUTION_OUT_DIR = os.path.join(BASE_DIR, "SAVE-DATA-PER-AGENT", "Execution-Agent-Output")

os.makedirs(EXECUTION_OUT_DIR, exist_ok=True)

class ExecutionAgent:
    def __init__(self):
        load_dotenv(find_dotenv())
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_SECRET_KEY")
        
        if not api_key or not api_secret:
            raise ValueError("Alpaca API credentials missing.")
            
        # Hardcoding paper=True for safety during Hackathon test phase
        self.trading_client = TradingClient(api_key, api_secret, paper=True)
        logger.info("✅ Alpaca Trading Client Initialized (Paper Mode)")

    def get_latest_risk_file(self):
        files = glob.glob(os.path.join(RISK_OUT_DIR, "*.json"))
        if not files:
            return None
        return max(files, key=os.path.getctime)

    def execute_trades(self):
        risk_file = self.get_latest_risk_file()
        if not risk_file:
            logger.error("No Risk Assessment Engine output found.")
            return

        with open(risk_file, 'r') as f:
            risk_data = json.load(f)

        source_decision_file = risk_data.get("source_file")
        if not source_decision_file:
            logger.error("Risk Assessment JSON is missing 'source_file' reference.")
            return

        decision_filepath = os.path.join(DECISION_OUT_DIR, source_decision_file)
        if not os.path.exists(decision_filepath):
            logger.error(f"Source decision file not found: {decision_filepath}")
            return

        with open(decision_filepath, 'r') as f:
            decision_data = json.load(f)

        decision_map = {d.get("symbol"): d for d in decision_data.get("decisions", [])}

        run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        execution_results = []

        for evaluation in risk_data.get("evaluations", []):
            symbol = evaluation.get("symbol")
            
            # The Risk Engine outputs "PASS" to mean it PASSED the risk checks and is approved.
            if evaluation.get("decision") != "PASS":
                logger.info(f"Skipping {symbol} - Risk Engine rejected it.")
                continue

            decision_details = decision_map.get(symbol)
            if not decision_details:
                logger.error(f"Could not find original decision details for {symbol}.")
                continue

            strategy = decision_details.get("strategy", {})
            risk_metrics = evaluation.get("risk", {})
            order_details = evaluation.get("order", {})

            # 1. Build Normalized JSON Payload
            normalized_payload = {
                "trade_id": f"{symbol}_{run_timestamp}",
                "symbol": symbol,
                "strategy": strategy,
                "risk_assessment": {
                    "decision": "PASS",
                    "approved_contracts": order_details.get("contracts", 0),
                    "approved_limit_price": order_details.get("limit_price", 0.0),
                    "max_loss_per_contract": risk_metrics.get("max_loss_per_contract"),
                    "max_loss_total": risk_metrics.get("max_loss_total"),
                    "max_profit_per_contract": risk_metrics.get("max_profit_per_contract"),
                    "max_profit_total": risk_metrics.get("max_profit_total"),
                    "risk_reward_ratio": risk_metrics.get("risk_reward_ratio"),
                    "breakeven": risk_metrics.get("breakeven"),
                    "checks": evaluation.get("checks", {})
                }
            }

            logger.info(f"Submitting Order for {symbol}: {normalized_payload['risk_assessment']['approved_contracts']} contracts @ {normalized_payload['risk_assessment']['approved_limit_price']}")

            # 2. Build Option Leg Requests
            alpaca_legs = []
            for leg in strategy.get("legs", []):
                occ_symbol = leg.get("symbol")
                if not occ_symbol:
                    logger.error(f"Missing OCC symbol in leg for {symbol}. Cannot execute.")
                    continue
                    
                action = leg.get("action", "").upper()
                side = OrderSide.BUY if action == "BUY" else OrderSide.SELL
                intent = PositionIntent.BUY_TO_OPEN if action == "BUY" else PositionIntent.SELL_TO_OPEN
                
                alpaca_legs.append(OptionLegRequest(
                    symbol=occ_symbol,
                    ratio_qty=1, # 1:1 ratio for standard spreads
                    side=side,
                    position_intent=intent
                ))

            if not alpaca_legs:
                logger.error(f"No valid legs constructed for {symbol}.")
                continue

            # 3. Construct Limit Order Request
            try:
                if len(alpaca_legs) > 1:
                    order_request = MarketOrderRequest(
                        qty=normalized_payload["risk_assessment"]["approved_contracts"],
                        type="market",
                        time_in_force=TimeInForce.DAY,
                        order_class=OrderClass.MLEG,
                        legs=alpaca_legs
                    )
                else:
                    order_request = MarketOrderRequest(
                        symbol=alpaca_legs[0].symbol,
                        qty=normalized_payload["risk_assessment"]["approved_contracts"],
                        side=alpaca_legs[0].side,
                        type="market",
                        time_in_force=TimeInForce.DAY
                    )
                
                response = self.trading_client.submit_order(order_data=order_request)
                logger.info(f"✅ Order submitted successfully! Alpaca ID: {response.id}")
                
                execution_results.append({
                    "trade_id": normalized_payload["trade_id"],
                    "symbol": symbol,
                    "status": str(response.status),
                    "alpaca_order_id": str(response.id),
                    "normalized_payload": normalized_payload
                })

            except Exception as e:
                logger.error(f"❌ Failed to submit order for {symbol}: {e}")
                execution_results.append({
                    "trade_id": normalized_payload["trade_id"],
                    "symbol": symbol,
                    "status": "FAILED",
                    "error": str(e),
                    "normalized_payload": normalized_payload
                })

        if execution_results:
            out_file = os.path.join(EXECUTION_OUT_DIR, f"execution_receipt_{run_timestamp}.json")
            with open(out_file, 'w') as f:
                json.dump(execution_results, f, indent=2)
            logger.info(f"💾 Saved Execution Receipts to {out_file}")
        else:
            logger.info("No trades were executed.")

if __name__ == "__main__":
    print("🚀 Execution Agent Starting")
    print("=" * 40)
    agent = ExecutionAgent()
    agent.execute_trades()
