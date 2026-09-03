import os
import json
import glob
import logging
from datetime import datetime
from dotenv import load_dotenv, find_dotenv

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import LimitOrderRequest, OptionLegRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass, PositionIntent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RISK_OUT_DIR = os.path.join(BASE_DIR, "SAVE-DATA-PER-AGENT", "Risk-Engine-Output")
DECISION_OUT_DIR = os.path.join(BASE_DIR, "SAVE-DATA-PER-AGENT", "Decision-Agent-Output")
EXECUTION_OUT_DIR = os.path.join(BASE_DIR, "SAVE-DATA-PER-AGENT", "Execution-Agent-Output")
MONITOR_OUT_DIR = os.path.join(BASE_DIR, "SAVE-DATA-PER-AGENT", "Position-Monitor-Output")
JOURNAL_DIR = os.path.join(BASE_DIR, "SAVE-DATA-PER-AGENT", "Trade-Journal-Output")
JOURNAL_FILE = os.path.join(JOURNAL_DIR, "trade_journal.json")

os.makedirs(EXECUTION_OUT_DIR, exist_ok=True)
os.makedirs(JOURNAL_DIR, exist_ok=True)

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

    def sync_journal(self):
        """Syncs PENDING orders in the journal with actual fill data from Alpaca."""
        if not os.path.exists(JOURNAL_FILE):
            return
            
        with open(JOURNAL_FILE, 'r') as f:
            try:
                journal = json.load(f)
            except json.JSONDecodeError:
                journal = []
                
        updated = False
        for entry in journal:
            if entry.get("status") == "PENDING" and "alpaca_order_id" in entry:
                try:
                    order = self.trading_client.get_order_by_id(entry["alpaca_order_id"])
                    if order.status.name == "FILLED":
                        filled_price = float(order.filled_avg_price)
                        entry["entry_price"] = filled_price
                        entry["entry_timestamp"] = str(order.filled_at)
                        entry["status"] = "OPEN"
                        
                        # Per-contract accounting
                        if filled_price > 0:
                            entry["initial_debit"] = abs(filled_price) * 100
                            entry["initial_credit"] = 0.0
                        else:
                            entry["initial_credit"] = abs(filled_price) * 100
                            entry["initial_debit"] = 0.0
                            
                        limit_price = float(order.limit_price) if order.limit_price else 0.0
                        slippage = filled_price - limit_price
                        logger.info(f"Journal Synced ENTRY: {entry['trade_id']} FILLED at {filled_price:.2f} (Requested Limit: {limit_price:.2f} | Slippage: {slippage:.2f})")
                        updated = True
                except Exception as e:
                    logger.error(f"Failed to sync order {entry['alpaca_order_id']}: {e}")
                    
            elif entry.get("status") == "PENDING_EXIT" and "exit_alpaca_order_id" in entry:
                try:
                    order = self.trading_client.get_order_by_id(entry["exit_alpaca_order_id"])
                    if order.status.name == "FILLED":
                        filled_price = float(order.filled_avg_price)
                        entry["exit_price"] = filled_price
                        entry["exit_timestamp"] = str(order.filled_at)
                        entry["status"] = "CLOSED"
                        
                        # Calculate realized PnL
                        qty = float(entry.get("quantity", 1))
                        if entry.get("initial_debit", 0) > 0:
                            # Debit strategy profit: sell (credit) > buy (debit)
                            # close value is credit received, so filled_price is negative
                            # current_close_value = abs(filled_price) * 100
                            current_close_value = -filled_price * 100 
                            pnl = current_close_value - entry["initial_debit"]
                            entry["realized_pnl"] = pnl * qty
                            entry["return_pct"] = (pnl / entry["initial_debit"]) * 100
                        else:
                            # Credit strategy profit: buy back (debit) < sell (credit)
                            # close value is debit paid, so filled_price is positive
                            current_close_cost = filled_price * 100
                            pnl = entry["initial_credit"] - current_close_cost
                            entry["realized_pnl"] = pnl * qty
                            entry["return_pct"] = (pnl / entry["initial_credit"]) * 100
                            
                        limit_price = float(order.limit_price) if order.limit_price else 0.0
                        slippage = filled_price - limit_price
                        logger.info(f"Journal Synced EXIT: {entry['trade_id']} CLOSED at {filled_price:.2f} (Requested Limit: {limit_price:.2f} | Slippage: {slippage:.2f})")
                        updated = True
                except Exception as e:
                    logger.error(f"Failed to sync exit order {entry['exit_alpaca_order_id']}: {e}")

        if updated:
            with open(JOURNAL_FILE, 'w') as f:
                json.dump(journal, f, indent=2)

    def append_to_journal(self, entry_dict):
        journal = []
        if os.path.exists(JOURNAL_FILE):
            with open(JOURNAL_FILE, 'r') as f:
                try:
                    journal = json.load(f)
                except json.JSONDecodeError:
                    pass
        journal.append(entry_dict)
        with open(JOURNAL_FILE, 'w') as f:
            json.dump(journal, f, indent=2)

    def update_journal_exit(self, strategy_id, exit_order_id, exit_reason):
        if not os.path.exists(JOURNAL_FILE):
            return
        with open(JOURNAL_FILE, 'r') as f:
            journal = json.load(f)
            
        for entry in journal:
            if entry.get("strategy_id") == strategy_id and entry.get("status") == "OPEN":
                entry["status"] = "PENDING_EXIT"
                entry["exit_alpaca_order_id"] = exit_order_id
                entry["exit_reason"] = exit_reason
                break
                
        with open(JOURNAL_FILE, 'w') as f:
            json.dump(journal, f, indent=2)

    def get_latest_risk_file(self):
        files = glob.glob(os.path.join(RISK_OUT_DIR, "*.json"))
        if not files:
            return None
        return max(files, key=os.path.getctime)

    def execute_trades(self):
        self.sync_journal()
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
            
            # The Risk Engine outputs "ACCEPT" to mean it passed the risk checks and is approved.
            if evaluation.get("decision") != "ACCEPT":
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
            trade_id = f"{symbol}_{run_timestamp}"
            normalized_payload = {
                "trade_id": trade_id,
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

            # 2. Build Option Leg Requests & Calculate Net Price
            alpaca_legs = []
            net_price = 0.0
            
            for leg in strategy.get("legs", []):
                occ_symbol = leg.get("symbol")
                if not occ_symbol:
                    logger.error(f"Missing OCC symbol in leg for {symbol}. Cannot execute.")
                    continue
                    
                action = leg.get("action", "").upper()
                side = OrderSide.BUY if action == "BUY" else OrderSide.SELL
                intent = PositionIntent.BUY_TO_OPEN if action == "BUY" else PositionIntent.SELL_TO_OPEN
                
                leg_price = float(leg.get("price", 0.0))
                if action == "BUY":
                    net_price += leg_price
                else:
                    net_price -= leg_price
                
                alpaca_legs.append(OptionLegRequest(
                    symbol=occ_symbol,
                    ratio_qty=1, # 1:1 ratio for standard spreads
                    side=side,
                    position_intent=intent
                ))

            if not alpaca_legs:
                logger.error(f"No valid legs constructed for {symbol}.")
                continue
                
            net_price = round(net_price, 2)
            approved_limit_price = normalized_payload['risk_assessment']['approved_limit_price']
            
            if "limit_price" not in order_details:
                logger.error(f"INVALID_MLEG_NET_PRICE: Risk Engine did not provide an approved_limit_price for {symbol}.")
                continue
                
            if abs(net_price - float(approved_limit_price)) > 0.05:
                logger.error(f"INVALID_MLEG_NET_PRICE: Calculated net price ({net_price}) differs significantly from approved limit price ({approved_limit_price}) for {symbol}. Aborting order.")
                continue

            is_mleg = len(alpaca_legs) > 1
            strat_name = strategy.get("type", "Unknown")
            contracts = normalized_payload["risk_assessment"]["approved_contracts"]
            
            leg_logs = []
            for leg in strategy.get("legs", []):
                sym = leg.get("symbol")
                bid = leg.get("bid", "N/A")
                ask = leg.get("ask", "N/A")
                mid = leg.get("mid", "N/A")
                leg_logs.append(f"  - {sym}: Bid={bid} | Ask={ask} | Mid={mid}")
            leg_log_str = "\n".join(leg_logs)
            
            if is_mleg:
                logger.info(f"Submitting MLeg Order:\nSymbol: {symbol}\nStrategy: {strat_name}\nContracts: {contracts}\nLegs:\n{leg_log_str}\nNet {'Debit' if net_price > 0 else 'Credit'}: ${abs(net_price):.2f}\nAlpaca limit_price: {net_price:.2f}")
            else:
                logger.info(f"Submitting Single-Leg Order for {symbol}:\nContracts: {contracts}\nLegs:\n{leg_log_str}\nAlpaca limit_price: {net_price:.2f}")

            # 3. Construct Limit Order Request
            try:
                if is_mleg:
                    order_request = LimitOrderRequest(
                        qty=contracts,
                        limit_price=net_price,
                        time_in_force=TimeInForce.DAY,
                        order_class=OrderClass.MLEG,
                        legs=alpaca_legs
                    )
                else:
                    order_request = LimitOrderRequest(
                        symbol=alpaca_legs[0].symbol,
                        qty=contracts,
                        limit_price=abs(net_price),
                        side=alpaca_legs[0].side,
                        time_in_force=TimeInForce.DAY
                    )
                
                response = self.trading_client.submit_order(order_data=order_request)
                logger.info(f"✅ Order submitted successfully! Alpaca ID: {response.id}")
                
                # Write to Journal
                journal_entry = {
                    "trade_id": trade_id,
                    "strategy_id": trade_id,
                    "symbol": symbol,
                    "strategy_type": strat_name,
                    "alpaca_order_id": str(response.id),
                    "status": "PENDING",
                    "quantity": contracts,
                    "max_risk": risk_metrics.get("max_loss_total"),
                    "legs": strategy.get("legs", [])
                }
                self.append_to_journal(journal_entry)
                
                execution_results.append({
                    "trade_id": trade_id,
                    "symbol": symbol,
                    "status": str(response.status),
                    "alpaca_order_id": str(response.id),
                    "normalized_payload": normalized_payload
                })

            except Exception as e:
                logger.error(f"❌ Failed to submit order for {symbol}: {e}")
                execution_results.append({
                    "trade_id": trade_id,
                    "symbol": symbol,
                    "status": "FAILED",
                    "error": str(e)
                })

        if execution_results:
            out_file = os.path.join(EXECUTION_OUT_DIR, f"execution_receipt_{run_timestamp}.json")
            with open(out_file, 'w') as f:
                json.dump(execution_results, f, indent=2)
            logger.info(f"💾 Saved Execution Receipts to {out_file}")

    def execute_exits(self):
        self.sync_journal()
        files = glob.glob(os.path.join(MONITOR_OUT_DIR, "exit_orders_*.json"))
        if not files:
            logger.info("No Exit Orders found.")
            return
            
        latest_file = max(files, key=os.path.getctime)
        with open(latest_file, 'r') as f:
            exit_data = json.load(f)
            
        # Delete file after reading so it isn't re-processed next cycle
        try:
            os.remove(latest_file)
        except Exception as e:
            logger.error(f"Failed to delete {latest_file}: {e}")
            
        directives = exit_data.get("exit_directives", [])
        if not directives:
            logger.info("No exit directives in payload.")
            return
            
        for directive in directives:
            strategy_id = directive.get("strategy_id")
            symbol = directive.get("symbol")
            quantity = directive.get("quantity")
            reason = directive.get("reason")
            provided_limit_price = directive.get("limit_price")
            legs = directive.get("legs", [])
            
            logger.info(f"Processing EXIT for {strategy_id} ({reason})")
            
            alpaca_legs = []
            calculated_net_price = 0.0
            
            for leg in legs:
                occ_symbol = leg.get("symbol")
                action = leg.get("action").upper()
                side = OrderSide.BUY if action == "BUY_TO_CLOSE" else OrderSide.SELL
                intent = PositionIntent.BUY_TO_CLOSE if action == "BUY_TO_CLOSE" else PositionIntent.SELL_TO_CLOSE
                
                # Alpaca Sign Convention Check:
                # Positive = Net Debit (we pay), Negative = Net Credit (we receive)
                price = leg.get("price", 0.0)
                if action == "BUY_TO_CLOSE":
                    calculated_net_price += price
                elif action == "SELL_TO_CLOSE":
                    calculated_net_price -= price
                    
                alpaca_legs.append(OptionLegRequest(
                    symbol=occ_symbol,
                    ratio_qty=1,
                    side=side,
                    position_intent=intent
                ))
                
            calculated_net_price = round(calculated_net_price, 2)
            
            if abs(calculated_net_price - float(provided_limit_price)) > 0.05:
                logger.error(f"❌ EXIT REJECTED {strategy_id}: Monitor limit_price ({provided_limit_price}) vs Calculated ({calculated_net_price}) discrepancy.")
                continue
                
            is_mleg = len(alpaca_legs) > 1
            try:
                if is_mleg:
                    order_request = LimitOrderRequest(
                        qty=quantity,
                        limit_price=calculated_net_price,
                        time_in_force=TimeInForce.DAY,
                        order_class=OrderClass.MLEG,
                        legs=alpaca_legs
                    )
                else:
                    order_request = LimitOrderRequest(
                        symbol=alpaca_legs[0].symbol,
                        qty=quantity,
                        limit_price=abs(calculated_net_price),
                        side=alpaca_legs[0].side,
                        position_intent=alpaca_legs[0].position_intent,
                        time_in_force=TimeInForce.DAY
                    )
                
                response = self.trading_client.submit_order(order_data=order_request)
                logger.info(f"✅ EXIT Order submitted! Alpaca ID: {response.id}")
                self.update_journal_exit(strategy_id, str(response.id), reason)
            except Exception as e:
                logger.error(f"❌ Failed to submit EXIT for {strategy_id}: {e}")

if __name__ == "__main__":
    import sys
    print("🚀 Execution Agent Starting")
    print("=" * 40)
    agent = ExecutionAgent()
    
    if "--exits-only" in sys.argv:
        agent.execute_exits()
    elif "--entries-only" in sys.argv:
        agent.execute_trades()
    else:
        # Default behavior if no args passed
        agent.execute_exits()
        agent.execute_trades()
