import os
import json
import glob
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv, find_dotenv

# Alpaca and Groq imports
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.requests import OptionChainRequest
from groq import Groq

# Load environment variables
load_dotenv(find_dotenv())

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# Directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKET_SCANNER_OUT_DIR = os.path.join(BASE_DIR, "Market Scanner Output")
NEWS_AGENT_OUT_DIR = os.path.join(BASE_DIR, "News Agent Output")
OPTIONS_AGENT_OUT_DIR = os.path.join(BASE_DIR, "Options Agent Output")

os.makedirs(OPTIONS_AGENT_OUT_DIR, exist_ok=True)

# Initialize Clients
alpaca_client = None
if ALPACA_API_KEY and ALPACA_SECRET_KEY:
    try:
        alpaca_client = OptionHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
    except Exception as e:
        print(f"Warning: Could not initialize Alpaca Option client: {e}")

groq_client = None
if GROQ_API_KEY:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        print(f"Warning: Could not initialize Groq client: {e}")


def get_latest_json_file(directory: str):
    """Finds the most recently modified JSON file in a directory."""
    if not os.path.exists(directory):
        return None
        
    json_files = glob.glob(os.path.join(directory, "*.json"))
    if not json_files:
        return None
        
    latest_file = max(json_files, key=os.path.getctime)
    return latest_file


def get_mock_data_processing_layer():
    """
    Extracts the dummy_input directly from market_scanner.py to serve as the
    mock Data Processing Layer output.
    """
    market_scanner_path = os.path.join(BASE_DIR, "Market-Scanner")
    if market_scanner_path not in sys.path:
        sys.path.insert(0, market_scanner_path)
        
    try:
        # Import the module to read the dummy_input variable
        import market_scanner
        # Create a dictionary keyed by symbol for easy lookup
        mock_data = {item['symbol']: item for item in market_scanner.dummy_input}
        return mock_data
    except ImportError as e:
        print(f"Failed to import market_scanner.py: {e}")
        return {}
    except AttributeError:
        print("dummy_input not found in market_scanner.py")
        return {}


def aggregate_candidate_data():
    """
    Reads the latest files from Market Scanner and News Agent,
    merges them with the mock Data Processing layer, and returns a list of candidates.
    """
    candidates = []
    
    # 1. Market Scanner (Provides symbol and scores)
    ms_file = get_latest_json_file(MARKET_SCANNER_OUT_DIR)
    if not ms_file:
        print(f"No Market Scanner output found in {MARKET_SCANNER_OUT_DIR}")
        return []
        
    with open(ms_file, 'r') as f:
        try:
            ms_data = json.load(f)
            if isinstance(ms_data, dict):
                if "candidates" in ms_data:
                    ms_candidates = ms_data["candidates"]
                elif "detailed_scores" in ms_data:
                    ms_candidates = ms_data["detailed_scores"].get("candidates", [])
                elif "overall_ranking" in ms_data:
                    ms_candidates = ms_data["overall_ranking"].get("candidates", [])
                else:
                    ms_candidates = [ms_data]
            else:
                ms_candidates = ms_data
        except json.JSONDecodeError:
            print(f"Failed to decode {ms_file}")
            return []

    # 2. News Agent (Provides news array)
    news_file = get_latest_json_file(NEWS_AGENT_OUT_DIR)
    news_data = {}
    if news_file:
        with open(news_file, 'r') as f:
            try:
                # Assume news data is a dict keyed by symbol or a list we can parse
                raw_news = json.load(f)
                if isinstance(raw_news, list):
                    for item in raw_news:
                        if 'symbol' in item:
                            news_data[item['symbol']] = item.get('news', [])
            except json.JSONDecodeError:
                print(f"Failed to decode {news_file}")
    
    # 3. Data Processing Mock (Provides price, returns, trend, volatility, volume)
    dp_mock_data = get_mock_data_processing_layer()
    
    # Merge Data
    for ms_cand in ms_candidates:
        symbol = ms_cand.get("symbol")
        if not symbol:
            continue
            
        dp_info = dp_mock_data.get(symbol, {})
        
        candidate = {
            "symbol": symbol,
            "price": dp_info.get("price", 0.0),
            "scores": {
                "opportunity": ms_cand.get("opportunity_score", dp_info.get("scores", {}).get("opportunity", 0)),
                "momentum": ms_cand.get("momentum", dp_info.get("scores", {}).get("momentum", 0)),
                "trend": ms_cand.get("trend", dp_info.get("scores", {}).get("trend", 0)),
                "volatility": ms_cand.get("volatility", dp_info.get("scores", {}).get("volatility", 0)),
                "news": ms_cand.get("news_score", dp_info.get("scores", {}).get("news", 0))
            },
            "market_data": {
                "rsi14": dp_info.get("trend", {}).get("rsi14", 0),
                "atr": dp_info.get("volatility", {}).get("atr", 0),
                "returns": dp_info.get("returns", {})
            },
            "news": news_data.get(symbol, dp_info.get("news", [])) # Fallback to mock news if agent hasn't run
        }
        
        # If we couldn't find a price, we can't fetch options, so skip.
        if candidate["price"] == 0.0:
            print(f"Skipping {symbol}: No price data found in Data Processing mock.")
            continue
            
        candidates.append(candidate)
        
    return candidates


def fetch_and_filter_options_chain(symbol: str, spot_price: float):
    if not alpaca_client:
        raise RuntimeError(f"Alpaca client not initialized. Cannot fetch options chain for {symbol}.")
    
    print(f"Fetching real options chain for {symbol} from Alpaca...")
    try:
        req = OptionChainRequest(underlying_symbol=symbol)
        chain_response = alpaca_client.get_option_chain(req)
    except Exception as e:
        print(f"Error fetching chain for {symbol}: {e}")
        return []

    raw_chain = []
    for occ_symbol, snapshot in chain_response.items():
        try:
            # Parse OCC Symbol using reverse indexing
            strike = float(occ_symbol[-8:]) / 1000.0
            option_type = 'call' if occ_symbol[-9:-8] == 'C' else 'put'
            exp_yymmdd = occ_symbol[-15:-9]
            expiration = f"20{exp_yymmdd[0:2]}-{exp_yymmdd[2:4]}-{exp_yymmdd[4:6]}"
            
            # Extract Quotes
            bid = snapshot.latest_quote.bid_price if snapshot.latest_quote else 0.0
            ask = snapshot.latest_quote.ask_price if snapshot.latest_quote else 0.0
            
            if bid == 0.0 and ask == 0.0 and snapshot.latest_trade:
                price = snapshot.latest_trade.price
                bid = price
                ask = price

            raw_chain.append({
                "symbol": occ_symbol,
                "type": option_type,
                "strike": strike,
                "expiration": expiration,
                "bid": bid,
                "ask": ask,
                "open_interest": 0, # Not provided natively
                "volume": 0, # Not provided natively
                "iv": snapshot.implied_volatility or 0.0,
                "delta": snapshot.greeks.delta if snapshot.greeks else 0.0
            })
        except Exception as e:
            continue
            
    print(f"Fetched {len(raw_chain)} raw contracts for {symbol}.")
    filtered = apply_python_filters(raw_chain, spot_price)
    print(f"Filtered down to {len(filtered)} liquid contracts for {symbol}.")
    return filtered


def apply_python_filters(raw_chain: list, spot_price: float):
    filtered_chain = []
    today = datetime.today()
    
    for contract in raw_chain:
        try:
            exp_date = datetime.strptime(contract['expiration'], "%Y-%m-%d")
            days_to_exp = (exp_date - today).days
            if not (15 <= days_to_exp <= 90):
                continue
        except ValueError:
            continue
            
        strike = contract.get('strike', 0)
        if not (spot_price * 0.90 <= strike <= spot_price * 1.10):
            continue
            
        bid = contract.get('bid')
        ask = contract.get('ask')
        if bid is None or ask is None or bid <= 0 or ask <= 0:
            continue
            
        mid_price = (bid + ask) / 2
        if mid_price > 0:
            spread_pct = (ask - bid) / mid_price
            # Strict spread check for liquidity (15%)
            if spread_pct > 0.15:
                continue
            contract['spread_pct'] = spread_pct
        else:
            continue
                
        filtered_chain.append(contract)
        
    # Sort by spread_pct (tightest first) and limit to 20 to prevent LLM TPM limits
    filtered_chain.sort(key=lambda x: x.get('spread_pct', 1.0))
    return filtered_chain[:20]





def generate_strategy(candidate: dict, filtered_chain: list) -> dict:
    if not groq_client:
        raise RuntimeError("Groq client not initialized. Cannot generate options strategy.")

    prompt = f"""
    You are an expert options trading agent.
    Analyze the following market candidate and propose ONE multi-leg options strategy.
    
    Candidate Symbol: {candidate.get('symbol')}
    Current Price: {candidate.get('price')}
    Scores: {json.dumps(candidate.get('scores', {}))}
    Market Data: {json.dumps(candidate.get('market_data', {}))}
    News: {json.dumps(candidate.get('news', {}))}
    
    Available Filtered Options Chain:
    {json.dumps(filtered_chain, indent=2)}
    
    You are strictly limited to ONLY these 6 strategy types. NEVER use Calendar or Diagonal spreads:
    1. "LongCall"
    2. "LongPut"
    3. "BullCallSpread"
    4. "BearPutSpread"
    5. "BearCallSpread"
    6. "BullPutSpread"
    
    Respond STRICTLY in JSON format with the following structure:
    {{
      "type": "StrategyName", (MUST be exactly one of the 6 approved types)
      "confidence": 0.0 to 1.0,
      "legs": [
        {{
          "action": "BUY" or "SELL",
          "option_type": "CALL" or "PUT",
          "strike": float,
          "expiration": "YYYY-MM-DD",
          "price": float (use Ask for BUY, Bid for SELL)
        }}
      ],
      "reason": "String explaining why this strategy fits."
    }}
    """
    
    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a specialized options trading JSON API."},
                {"role": "user", "content": prompt}
            ],
            model=GROQ_MODEL,
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error calling Groq API: {e}")
        return {}


def validate_and_calculate_metrics(strategy: dict, filtered_chain: list) -> dict:
    if not strategy or "legs" not in strategy:
        return {"error": "Invalid strategy format"}

    validated_legs = []
    cost_per_share = 0.0
    
    for leg in strategy['legs']:
        action = leg.get('action', '').upper()
        option_type = leg.get('option_type', '').lower()
        strike = float(leg.get('strike', 0))
        expiration = leg.get('expiration', '')
        
        matched_contract = None
        for contract in filtered_chain:
            if (contract['type'].lower() == option_type and 
                float(contract['strike']) == strike and 
                contract['expiration'] == expiration):
                matched_contract = contract
                break
                
        if not matched_contract:
            return {"error": f"LLM suggested contract not found in chain: {option_type} {strike} {expiration}"}
            
        if action == "BUY":
            price = matched_contract['ask']
            cost_per_share += price
        elif action == "SELL":
            price = matched_contract['bid']
            cost_per_share -= price
        else:
            return {"error": f"Invalid action: {action}"}
            
        validated_legs.append({
            "symbol": matched_contract['symbol'],
            "action": action,
            "option_type": option_type.upper(),
            "strike": strike,
            "expiration": expiration,
            "price": price
        })
        
    net_cost = cost_per_share
    
    if len(validated_legs) == 1:
        leg = validated_legs[0]
        if leg['action'] == 'BUY':
            max_loss = leg['price']
            max_profit = float('inf')
            breakeven = leg['strike'] + leg['price'] if leg['option_type'] == 'CALL' else leg['strike'] - leg['price']
        else:
            max_profit = leg['price']
            max_loss = float('inf')
            breakeven = leg['strike'] + leg['price'] if leg['option_type'] == 'CALL' else leg['strike'] - leg['price']
    elif len(validated_legs) == 2:
        legs = sorted(validated_legs, key=lambda x: x.get('strike', 0.0))
        leg1 = legs[0]
        leg2 = legs[1]
        strike_width = leg2['strike'] - leg1['strike']
        op_type1 = leg1['option_type']
        op_type2 = leg2['option_type']
        
        if op_type1 == op_type2:
            if net_cost > 0: # Debit spread
                max_loss = net_cost
                max_profit = strike_width - net_cost
                if op_type1 == 'CALL':
                    breakeven = leg1['strike'] + net_cost
                else:
                    breakeven = leg2['strike'] - net_cost
            else: # Credit spread
                max_profit = abs(net_cost)
                max_loss = strike_width - max_profit
                if op_type1 == 'CALL':
                    breakeven = leg1['strike'] + max_profit
                else:
                    breakeven = leg2['strike'] - max_profit
        else:
            return {"error": "Unsupported 2-leg strategy (types differ)"}
    else:
        return {"error": "Unsupported strategy structure: too many legs"}
        
    risk_reward = (max_profit / max_loss) if max_loss > 0 and max_loss != float('inf') else float('inf')

    if max_profit < 0 or max_loss < 0:
        return {"error": "Strategy yields guaranteed loss or negative max loss."}
        
    return {
        "net_debit": round(net_cost, 2), 
        "max_profit": round(max_profit, 2) if max_profit != float('inf') else float('inf'),
        "max_loss": round(max_loss, 2) if max_loss != float('inf') else float('inf'),
        "breakeven": round(breakeven, 2),
        "risk_reward_ratio": round(risk_reward, 2),
        "validated_legs": validated_legs
    }


def run_options_agent():
    print("Starting Options Agent Data Aggregation...")
    candidates = aggregate_candidate_data()
    
    if not candidates:
        print("No candidates were aggregated from the pipeline. Exiting.")
        return
        
    print(f"Successfully aggregated {len(candidates)} candidate(s).")
    results = []
    
    for candidate in candidates:
        symbol = candidate['symbol']
        spot_price = candidate['price']
        print(f"Processing candidate: {symbol} at ${spot_price}")
        
        filtered_chain = fetch_and_filter_options_chain(symbol, spot_price)
        if not filtered_chain:
            msg = f"No valid options found for {symbol}."
            print(msg)
            results.append({"symbol": symbol, "error": msg})
            continue
            
        raw_strategy = generate_strategy(candidate, filtered_chain)
        if not raw_strategy or "type" not in raw_strategy:
            msg = "LLM failed to generate a valid strategy."
            print(msg)
            results.append({"symbol": symbol, "error": msg})
            continue
            
        metrics = validate_and_calculate_metrics(raw_strategy, filtered_chain)
        if "error" in metrics:
            msg = f"Strategy rejected: {metrics['error']}"
            print(msg)
            results.append({"symbol": symbol, "error": msg})
            continue
            
        final_output = {
            "symbol": symbol,
            "strategy": {
                "type": raw_strategy["type"],
                "confidence": raw_strategy.get("confidence"),
                "legs": metrics["validated_legs"],
                "risk_reward": {
                    "net_debit": metrics["net_debit"],
                    "max_profit": metrics["max_profit"],
                    "max_loss": metrics["max_loss"],
                    "breakeven": metrics["breakeven"],
                    "risk_reward_ratio": metrics["risk_reward_ratio"]
                },
                "reason": raw_strategy.get("reason", "")
            }
        }
        results.append(final_output)
        
    # Save Output
    if results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = os.path.join(OPTIONS_AGENT_OUT_DIR, f"options_strategy_{timestamp}.json")
        with open(out_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nSaved final strategy proposals to {out_file}")
    else:
        print("\nNo valid strategies generated.")
    
if __name__ == "__main__":
    run_options_agent()
