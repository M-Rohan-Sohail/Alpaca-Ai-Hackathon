import os
import glob
import json
import time
import subprocess
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from alpaca.trading.client import TradingClient

load_dotenv()

app = FastAPI(title="Alpaca Trading Terminal API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(BASE_DIR, "SAVE-DATA-PER-AGENT")
CONFIG_PATH = os.path.join(BASE_DIR, "User_Config", "config.json")

@app.on_event("startup")
def startup_event():
    daemon_script = os.path.join(BASE_DIR, "fast_exit_daemon.py")
    pid_file = os.path.join(BASE_DIR, "fast_exit_daemon.pid")
    
    daemon_running = False
    if os.path.exists(pid_file):
        try:
            with open(pid_file, 'r') as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, 0)
            daemon_running = True
            print(f"🔄 Fast Exit Daemon is already running (PID: {old_pid}).")
        except (ValueError, OSError):
            pass
            
    if not daemon_running:
        print("🚀 Launching Fast Exit Daemon as a Subprocess...")
        subprocess.Popen(
            [sys.executable, daemon_script],
            cwd=BASE_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        print("✅ Fast Exit Daemon is Running at Subprocess")

@app.get("/")
def read_root():
    return {"status": "Alpaca API Server is Running!"}

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    return {}

def get_latest_json(folder: str) -> Optional[Any]:
    path = os.path.join(SAVE_DIR, folder)
    if not os.path.exists(path):
        return None
    files = glob.glob(os.path.join(path, "*.json"))
    if not files:
        return None
    latest = max(files, key=os.path.getctime)
    try:
        with open(latest, 'r') as f:
            return json.load(f)
    except:
        return None

def get_journal() -> List[Dict]:
    journal_path = os.path.join(SAVE_DIR, "Trade-Journal-Output", "trade_journal.json")
    if os.path.exists(journal_path):
        try:
            with open(journal_path, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)

@app.get("/api/dashboard")
def get_dashboard():
    config = load_config()
    journal = get_journal()
    
    open_positions = len([j for j in journal if j.get("status") == "OPEN"])
    
    try:
        account = trading_client.get_account()
        equity = float(account.equity)
        buying_power = float(account.buying_power)
    except Exception as e:
        equity = 0.0
        buying_power = 0.0
        print(f"Error fetching account: {e}")

    daily_loss_used = 0.0
    daily_loss_limit = equity * (config.get("max_daily_loss_pct", 5.0) / 100)
    
    exposure_used = sum([j.get("max_loss") or j.get("max_risk") or 0 for j in journal if j.get("status") == "OPEN"])
    exposure_limit = equity * (config.get("max_exposure_pct", 20.0) / 100)
    
    exec_path = os.path.join(SAVE_DIR, "Execution-Agent-Output")
    recent_activity = []
    if os.path.exists(exec_path):
        files = sorted(glob.glob(os.path.join(exec_path, "*.json")), key=os.path.getctime, reverse=True)
        for f in files[:5]:
            try:
                with open(f, 'r') as fp:
                    receipts = json.load(fp)
                    for r in receipts:
                        if r.get("status") in ["FILLED", "SUBMITTED", "REJECTED", "OrderStatus.PENDING_NEW", "OrderStatus.FILLED", "OrderStatus.REJECTED"]:
                            recent_activity.append({
                                "id": r.get("order_id") or str(time.time()),
                                "timestamp": r.get("filled_at") or r.get("submitted_at") or datetime.now().isoformat(),
                                "type": "FILL" if "FILLED" in r.get("status") else "TRADE" if ("SUBMITTED" in r.get("status") or "PENDING" in r.get("status")) else "REJECT",
                                "message": f"{r.get('symbol')} order {r.get('status').lower()}",
                                "symbol": r.get("symbol")
                            })
            except:
                pass
                
    return {
        "equity": equity,
        "buying_power": buying_power,
        "daily_loss_used": daily_loss_used,
        "daily_loss_limit": daily_loss_limit,
        "exposure_used": exposure_used,
        "exposure_limit": exposure_limit,
        "open_positions": open_positions,
        "max_positions": config.get("max_concurrent_positions", 5),
        "updated_at": datetime.now().isoformat(),
        "recent_activity": recent_activity
    }

@app.get("/api/pipeline/latest")
def get_pipeline():
    det_data = get_latest_json("Deterministic-Filter-Output") or {}
    det = det_data.get("detailed_scores", {}).get("candidates", [])
    
    market_raw = get_latest_json("Market-Agent-Output") or {}
    market_list = market_raw.get("analyses", []) if isinstance(market_raw, dict) else market_raw
    market = {item.get("symbol"): item for item in market_list} if isinstance(market_list, list) else {}

    news_raw = get_latest_json("News-Agent-Output") or {}
    news_list = news_raw.get("news_analysis", []) if isinstance(news_raw, dict) else news_raw
    news = {item.get("symbol"): item for item in news_list} if isinstance(news_list, list) else {}

    options_raw = get_latest_json("Options-Agent-Output") or []
    options_list = options_raw if isinstance(options_raw, list) else options_raw.get("strategies", [])
    options = {item.get("symbol"): item for item in options_list} if isinstance(options_list, list) else {}

    decision_raw = get_latest_json("Decision-Agent-Output") or {}
    decision_list = decision_raw.get("decisions", []) if isinstance(decision_raw, dict) else decision_raw
    decision = {item.get("symbol"): item for item in decision_list} if isinstance(decision_list, list) else {}

    risk_raw = get_latest_json("Risk-Engine-Output") or {}
    risk_list = risk_raw.get("evaluations", []) if isinstance(risk_raw, dict) else risk_raw
    risk = {item.get("symbol"): item for item in risk_list} if isinstance(risk_list, list) else {}

    execution = get_latest_json("Execution-Agent-Output") or []
    exec_map = {r.get("symbol"): r for r in execution}

    candidates = []
    for base in det:
        symbol = base.get("symbol")
        
        stage = "DATA_PROCESSING"
        if symbol in market or symbol in news: stage = "MARKET_NEWS"
        if symbol in options: stage = "OPTIONS"
        if symbol in decision: stage = "DECISION"
        if symbol in risk: stage = "RISK"
        if symbol in exec_map: stage = "EXECUTION"
        if symbol in exec_map and exec_map[symbol].get("status") in ["FILLED", "REJECTED"]: stage = "DONE"
        
        m_data = market.get(symbol, {})
        n_data = news.get(symbol, {})
        o_data = options.get(symbol)
        d_data = decision.get(symbol, {})
        r_data = risk.get(symbol, {})
        e_data = exec_map.get(symbol, {})
        
        c = {
            "symbol": symbol,
            "updated_at": datetime.now().isoformat(),
            "stage": stage,
            "scores": {
                "trend": base.get("scores", {}).get("trend"),
                "momentum": base.get("scores", {}).get("momentum"),
                "volume": base.get("scores", {}).get("volume"),
                "filter_passed": True
            },
            "analysis": {
                "direction": m_data.get("direction"),
                "ai_confidence": m_data.get("confidence"),
                "summary": m_data.get("reasoning")
            },
            "news": {
                "sentiment": n_data.get("overall_sentiment") or n_data.get("sentiment"),
                "news_score": n_data.get("news_score"),
                "headlines": [h.get("headline", h.get("title", "")) for h in n_data.get("events", n_data.get("articles", []))]
            },
            "strategy": None,
            "decisions": [],
            "evaluations": [],
            "execution": {
                "status": e_data.get("status", "NOT_SUBMITTED"),
                "order_id": e_data.get("order_id"),
                "filled_at": e_data.get("filled_at")
            }
        }
        
        if o_data:
            strat = o_data.get("strategy") if isinstance(o_data.get("strategy"), dict) else o_data
            import math
            def safe_float(v):
                if v is None: return None
                if isinstance(v, str) and v.lower() == "unlimited": return 999999.0
                try:
                    f = float(v)
                    return 999999.0 if math.isinf(f) else f
                except:
                    return None

            c["strategy"] = {
                "type": strat.get("strategy_type") or strat.get("type"),
                "legs": strat.get("legs", []),
                "max_loss": safe_float(strat.get("max_loss") or strat.get("risk_reward", {}).get("max_loss")),
                "max_profit": safe_float(strat.get("max_profit") or strat.get("risk_reward", {}).get("max_profit")),
                "breakeven": strat.get("breakeven") or strat.get("risk_reward", {}).get("breakeven", [])
            }
            
        if d_data:
            c["decisions"].append({
                "decision": d_data.get("decision"),
                "reasoning": d_data.get("reasoning"),
                "confidence": d_data.get("confidence", 1.0)
            })
            
        if r_data:
            c["evaluations"].append({
                "decision": r_data.get("decision"),
                "checks": r_data.get("checks", {}),
                "order": {
                    "contracts": o_data.get("quantity", 1) if o_data else 1,
                    "capital_at_risk": o_data.get("max_loss", 0) if o_data else 0
                } if r_data.get("decision") == "ACCEPT" else None,
                "binding_constraint": r_data.get("binding_constraint"),
                "rejection_reasons": r_data.get("rejection_reasons", [])
            })
            
        candidates.append(c)
        
    return candidates

@app.get("/api/positions")
def get_positions():
    journal = get_journal()
    open_trades = [j for j in journal if j.get("status") == "OPEN"]
    
    try:
        alpaca_positions = trading_client.get_all_positions()
        alpaca_map = {p.symbol: p for p in alpaca_positions}
    except Exception as e:
        print(f"Error fetching alpaca positions: {e}")
        alpaca_map = {}

    positions_res = []
    for trade in open_trades:
        current_value = 0.0
        unrealized_pnl = 0.0
        
        for leg in trade.get("legs", []):
            occ = leg.get("symbol")
            if occ in alpaca_map:
                ap = alpaca_map[occ]
                current_value += abs(float(ap.market_value)) 
                unrealized_pnl += float(ap.unrealized_pl)
                
        entry_time_str = trade.get("entry_time", datetime.now().isoformat())
        try:
            entry_dt = datetime.fromisoformat(entry_time_str)
            days_held = max(0, (datetime.now() - entry_dt).days)
        except:
            days_held = 0

        max_loss = trade.get("max_loss") or trade.get("max_risk") or 1
        if max_loss == 0: max_loss = 1

        positions_res.append({
            "strategy_id": trade.get("strategy_id", f"pos_{trade.get('symbol')}"),
            "symbol": trade.get("symbol"),
            "strategy_type": trade.get("strategy_type"),
            "quantity": trade.get("quantity", 1),
            "legs": trade.get("legs", []),
            "entry_price": trade.get("entry_price", 0),
            "current_value": current_value,
            "unrealized_pnl": unrealized_pnl,
            "return_pct": (unrealized_pnl / max_loss) * 100 if unrealized_pnl else 0,
            "max_loss": trade.get("max_loss") or trade.get("max_risk"),
            "max_profit": trade.get("max_profit"),
            "breakeven": trade.get("breakeven", []),
            "dte": trade.get("min_dte", 0),
            "days_held": days_held,
            "exit_status": trade.get("exit_status", "HOLDING"),
            "entry_time": entry_time_str
        })
        
    return positions_res

@app.get("/api/journal")
def get_journal_api():
    journal = get_journal()
    return [j for j in journal if j.get("status") == "CLOSED"]

@app.post("/api/execute/pipeline")
def start_pipeline():
    pipeline_script = os.path.join(BASE_DIR, "Run_Pipeline.py")
    log_file = open(os.path.join(BASE_DIR, "pipeline.log"), "w")
    subprocess.Popen(
        [sys.executable, pipeline_script],
        cwd=BASE_DIR,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True
    )
    return {"status": "SUBMITTED"}

@app.get("/api/pipeline/status")
def get_pipeline_status():
    try:
        output = subprocess.check_output(["pgrep", "-f", "Run_Pipeline.py"]).decode()
        if output.strip():
            return {"is_running": True}
    except subprocess.CalledProcessError:
        pass
    return {"is_running": False}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True, ws="none")
