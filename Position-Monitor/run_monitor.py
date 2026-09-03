import os
import json
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv, find_dotenv

from alpaca.trading.client import TradingClient
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.requests import OptionChainRequest

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOURNAL_FILE = os.path.join(BASE_DIR, "SAVE-DATA-PER-AGENT", "Trade-Journal-Output", "trade_journal.json")
MONITOR_OUT_DIR = os.path.join(BASE_DIR, "SAVE-DATA-PER-AGENT", "Position-Monitor-Output")
CONFIG_FILE = os.path.join(BASE_DIR, "User_Config", "config.json")

os.makedirs(MONITOR_OUT_DIR, exist_ok=True)

class PositionMonitor:
    def __init__(self):
        load_dotenv(find_dotenv())
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_SECRET_KEY")
        
        if not api_key or not api_secret:
            raise ValueError("Alpaca API credentials missing.")
            
        self.trading_client = TradingClient(api_key, api_secret, paper=True)
        self.option_client = OptionHistoricalDataClient(api_key, api_secret)
        
        with open(CONFIG_FILE, 'r') as f:
            self.config = json.load(f).get("exit_rules", {})
            
    def run(self):
        logger.info("🛡️ Position Monitor Starting")
        
        if not os.path.exists(JOURNAL_FILE):
            logger.info("No Trade Journal found. Exiting.")
            return
            
        with open(JOURNAL_FILE, 'r') as f:
            try:
                journal = json.load(f)
            except json.JSONDecodeError:
                logger.error("Trade Journal is empty or corrupt.")
                return
                
        open_strategies = [e for e in journal if e.get("status") == "OPEN"]
        if not open_strategies:
            logger.info("No OPEN strategies found in Trade Journal.")
            return
            
        try:
            alpaca_positions = self.trading_client.get_all_positions()
            alpaca_symbols = {p.symbol for p in alpaca_positions}
        except Exception as e:
            logger.error(f"Failed to fetch Alpaca positions: {e}")
            return
            
        exit_directives = []
        
        for strategy in open_strategies:
            strategy_id = strategy.get("strategy_id")
            symbol = strategy.get("symbol")
            legs = strategy.get("legs", [])
            quantity = strategy.get("quantity", 1)
            
            # Verify legs exist in current Alpaca portfolio
            has_legs = True
            for leg in legs:
                if leg.get("symbol") not in alpaca_symbols:
                    logger.warning(f"Strategy {strategy_id} leg {leg.get('symbol')} missing from portfolio. Skipping.")
                    has_legs = False
                    break
            
            if not has_legs:
                continue
                
            try:
                req = OptionChainRequest(underlying_symbol=symbol)
                chain_response = self.option_client.get_option_chain(req)
            except Exception as e:
                logger.error(f"Failed to fetch option chain for {symbol}: {e}")
                continue
                
            limit_price = 0.0
            closing_legs = []
            valid_pricing = True
            min_dte = 9999
            
            for leg in legs:
                occ_symbol = leg.get("symbol")
                entry_action = leg.get("action", "").upper()
                
                snapshot = chain_response.get(occ_symbol)
                if not snapshot or not snapshot.latest_quote:
                    logger.warning(f"Missing quote for {occ_symbol}")
                    valid_pricing = False
                    break
                    
                bid = float(snapshot.latest_quote.bid_price)
                ask = float(snapshot.latest_quote.ask_price)
                
                # Expiration parsing
                exp_date_str = leg.get("expiration")
                if exp_date_str:
                    try:
                        exp_date = datetime.strptime(exp_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                        dte = (exp_date - datetime.now(timezone.utc)).days
                        min_dte = min(min_dte, dte)
                    except ValueError:
                        pass
                
                if entry_action == "BUY":
                    # LONG leg -> SELL_TO_CLOSE -> receive BID
                    action = "SELL_TO_CLOSE"
                    price = bid
                    limit_price -= price
                else:
                    # SHORT leg -> BUY_TO_CLOSE -> pay ASK
                    action = "BUY_TO_CLOSE"
                    price = ask
                    limit_price += price
                    
                closing_legs.append({
                    "symbol": occ_symbol,
                    "action": action,
                    "qty": quantity,
                    "price": price
                })
                
            if not valid_pricing:
                continue
                
            limit_price = round(limit_price, 2)
            
            # P&L Calculation
            initial_debit = float(strategy.get("initial_debit", 0.0))
            initial_credit = float(strategy.get("initial_credit", 0.0))
            current_pnl = 0.0
            return_pct = 0.0
            
            if initial_debit > 0:
                # Debit strategy: sell to close. Limit price should be negative (credit)
                closing_net_credit = -limit_price * 100
                current_pnl = closing_net_credit - initial_debit
                return_pct = (current_pnl / initial_debit) * 100
            elif initial_credit > 0:
                # Credit strategy: buy to close. Limit price should be positive (debit)
                closing_net_debit = limit_price * 100
                current_pnl = initial_credit - closing_net_debit
                return_pct = (current_pnl / initial_credit) * 100
                
            # Entry timestamp and holding days
            entry_ts_str = strategy.get("entry_timestamp")
            days_held = 0
            hours_held = 0
            if entry_ts_str:
                entry_ts = datetime.fromisoformat(entry_ts_str.replace('Z', '+00:00'))
                delta = datetime.now(timezone.utc) - entry_ts
                days_held = delta.days
                hours_held = delta.total_seconds() / 3600
                
            # Rule Evaluation (Priority Order)
            exit_reason = None
            
            if min_dte <= 0:
                exit_reason = "EXPIRED_OR_EXPIRING"
            elif return_pct <= self.config.get("stop_loss_pct", -25.0) and hours_held >= (5 / 60):
                exit_reason = "STOP_LOSS"
            elif return_pct >= self.config.get("take_profit_pct", 50.0):
                exit_reason = "TAKE_PROFIT"
            elif min_dte <= self.config.get("max_dte", 3):
                exit_reason = "DTE_LIMIT"
            elif days_held >= self.config.get("max_holding_days", 10):
                exit_reason = "MAX_HOLDING_PERIOD"
                
            logger.info(f"Monitor {strategy_id}: PNL={return_pct:.2f}%, DTE={min_dte}, Held={days_held}d -> Reason: {exit_reason or 'HOLD'}")
                
            if exit_reason:
                exit_directives.append({
                    "strategy_id": strategy_id,
                    "symbol": symbol,
                    "strategy_type": strategy.get("strategy_type"),
                    "action": "EXIT",
                    "reason": exit_reason,
                    "quantity": quantity,
                    "limit_price": limit_price,
                    "current_pnl_pct": round(return_pct, 2),
                    "legs": closing_legs
                })
                
        if exit_directives:
            run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_file = os.path.join(MONITOR_OUT_DIR, f"exit_orders_{run_timestamp}.json")
            with open(out_file, 'w') as f:
                json.dump({"exit_directives": exit_directives}, f, indent=2)
            logger.info(f"💾 Flagged {len(exit_directives)} strategies for exit.")
        else:
            logger.info("No strategies flagged for exit.")
            
if __name__ == "__main__":
    monitor = PositionMonitor()
    monitor.run()
