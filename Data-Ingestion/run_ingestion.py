import os
import sys
import json
import time
import re
from datetime import datetime, timedelta, timezone
import requests
from dotenv import load_dotenv

# Ensure we can import from User_Config if running from root or from Data-Ingestion directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from User_Config.config import load_config
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.requests import OptionChainRequest
from alpaca.data.timeframe import TimeFrame

# Load keys from .env into environment variables (must use ROOT_DIR to find .env reliably)
load_dotenv(os.path.join(ROOT_DIR, ".env"))

ALPACA_KEY = os.environ["ALPACA_API_KEY"]
ALPACA_SECRET = os.environ["ALPACA_SECRET_KEY"]
SERPER_KEY = os.environ["SERPER_API_KEY"]

# Create clients once - every function below reuses these
stock_client = StockHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)
option_client = OptionHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)


def get_stock_bars(symbols: list[str], limit: int = 100):
    start_date = datetime.now(timezone.utc) - timedelta(days=100)
    request = StockBarsRequest(
        symbol_or_symbols=symbols,
        timeframe=TimeFrame.Day,
        start=start_date,
        limit=limit
    )
    return stock_client.get_stock_bars(request)


def get_option_chain(symbol: str):
    request = OptionChainRequest(underlying_symbol=symbol)
    return option_client.get_option_chain(request)


def get_news(symbol: str, top_n: int = 3, retries: int = 3):
    headers = {"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"}
    params = {"q": f"{symbol} stock news"}

    for attempt in range(retries):
        response = requests.post(
            "https://google.serper.dev/search",
            json=params,
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            all_results = data.get("organic", [])
            return all_results[:top_n]
        elif response.status_code in (429, 500, 502, 503):
            wait = 2 ** attempt
            print(f"Serper error {response.status_code}, retrying in {wait}s...")
            time.sleep(wait)
        else:
            response.raise_for_status()

    raise RuntimeError(f"Failed to fetch news for {symbol} after {retries} tries")


def get_run_folder_name(base_folder: str, timestamp: str) -> str:
    """
    Deletes previous DI_RUN folders and returns the new folder name.
    """
    import shutil
    os.makedirs(base_folder, exist_ok=True)
    existing_runs = [d for d in os.listdir(base_folder) if d.startswith("DI_RUN_") and os.path.isdir(os.path.join(base_folder, d))]
    
    for d in existing_runs:
        shutil.rmtree(os.path.join(base_folder, d))
        
    return f"DI_RUN_1_{timestamp}"


def save_json(data, folder: str, symbol: str, data_type: str):
    """
    Saves `data` to <folder>/<data_type>/<symbol>_<data_type>.json
    """
    target_dir = os.path.join(folder, data_type)
    os.makedirs(target_dir, exist_ok=True)
    filename = f"{symbol}_{data_type}.json"
    filepath = os.path.join(target_dir, filename)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved: {filepath}")


def parse_option_symbol(symbol: str) -> dict:
    match = re.match(r"^([A-Z.]+)(\d{6})([CP])(\d{8})$", symbol)
    if not match:
        return {"exp": None, "type": None, "strike": None}

    underlying, date_str, opt_type, strike_str = match.groups()
    exp_date = f"20{date_str[0:2]}-{date_str[2:4]}-{date_str[4:6]}"
    strike = int(strike_str) / 1000

    return {
        "exp": exp_date,
        "type": "CALL" if opt_type == "C" else "PUT",
        "strike": strike
    }


def fetch_bars(symbol: str, run_folder: str):
    bars = get_stock_bars([symbol])
    bars_list = [
        {
            "t": str(b.timestamp),
            "o": b.open,
            "h": b.high,
            "l": b.low,
            "c": b.close,
            "v": b.volume
        }
        for b in bars[symbol]
    ]
    save_json(bars_list, run_folder, symbol, "bars")


def fetch_news(symbol: str, run_folder: str):
    news = get_news(symbol)
    save_json(news, run_folder, symbol, "news")


def fetch_options(symbol: str, run_folder: str):
    chain = get_option_chain(symbol)
    options_list = []

    for opt_symbol, contract in chain.items():
        parsed = parse_option_symbol(opt_symbol)

        bid_price = None
        ask_price = None
        if contract.latest_quote is not None:
            bid_price = contract.latest_quote.bid_price
            ask_price = contract.latest_quote.ask_price

        delta = None
        if contract.greeks is not None:
            delta = contract.greeks.delta

        options_list.append({
            "symbol": opt_symbol,
            "strike": parsed["strike"],
            "exp": parsed["exp"],
            "type": parsed["type"],
            "bid": bid_price,
            "ask": ask_price,
            "iv": contract.implied_volatility,
            "delta": delta,
        })

    save_json(options_list, run_folder, symbol, "options")


def fetch_mcp_account_info(run_folder: str):
    import asyncio
    from mcp_client import AlpacaMCPClient
    client = AlpacaMCPClient()
    print("Fetching Account Info via MCP...")
    # Will raise if fails, strictly enforcing the MCP rule
    account_data = asyncio.run(client.call_tool("get_account_info", {}))
    
    target_dir = os.path.join(run_folder, "account")
    os.makedirs(target_dir, exist_ok=True)
    filepath = os.path.join(target_dir, "account_info.json")
    with open(filepath, "w") as f:
        json.dump(account_data, f, indent=2)
    print(f"Saved MCP Account Data: {filepath}")

def fetch_mcp_snapshot(symbol: str, run_folder: str):
    import asyncio
    from mcp_client import AlpacaMCPClient
    client = AlpacaMCPClient()
    print(f"Fetching Snapshot for {symbol} via MCP...")
    # Use "symbols" as per Alpaca MCP spec for snapshots
    snapshot_data = asyncio.run(client.call_tool("get_stock_snapshot", {"symbols": symbol}))
    
    target_dir = os.path.join(run_folder, "snapshot")
    os.makedirs(target_dir, exist_ok=True)
    filepath = os.path.join(target_dir, f"{symbol}_snapshot.json")
    with open(filepath, "w") as f:
        json.dump(snapshot_data, f, indent=2)
    print(f"Saved MCP Snapshot Data: {filepath}")


def fetch_and_cache(symbol: str, run_folder: str):
    # MCP Required Data - Strict Failure if unavailable
    try:
        fetch_mcp_snapshot(symbol, run_folder)
    except Exception as e:
        print(f"FATAL: Could not fetch MCP snapshot for {symbol}: {e}")
        raise RuntimeError("MCP Required Capability Failed") from e

    # Fallback to alpaca-py only for historical bars (unsupported natively in MCP as multiple days)
    try:
        fetch_bars(symbol, run_folder)
    except Exception as e:
        print(f"Could not fetch bars for {symbol}: {e}")

    try:
        fetch_news(symbol, run_folder)
    except Exception as e:
        print(f"Could not fetch news for {symbol}: {e}")

    try:
        fetch_options(symbol, run_folder)
    except Exception as e:
        print(f"Could not fetch options for {symbol}: {e}")


if __name__ == "__main__":
    # Validate and load config first
    config_path = os.path.join(ROOT_DIR, "User_Config", "config.json")
    print("Loading and verifying User Config...")
    config = load_config(config_path)
    print("User Config verified successfully.")
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    # Setup Data-Ingestion base folder
    data_ingestion_dir = os.path.join(ROOT_DIR, "SAVE-DATA-PER-AGENT", "Data-Ingestion-Output")
    
    # Get the specific run folder
    run_folder_name = get_run_folder_name(data_ingestion_dir, timestamp)
    run_folder_path = os.path.join(data_ingestion_dir, run_folder_name)
    
    print(f"Saving data to: {run_folder_path}")

    # Enforce MCP utilization for Account Info first
    try:
        fetch_mcp_account_info(run_folder_path)
    except Exception as e:
        print(f"FATAL: MCP Failed to fetch account info: {e}")
        sys.exit(1)

    for symbol in config.assets:
        print(f"\nFetching data for {symbol}...")
        fetch_and_cache(symbol, run_folder_path)

    print("\nDone caching sample data.")
