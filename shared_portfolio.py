import re
from collections import defaultdict
from typing import List, Dict, Any

def parse_occ(occ_symbol: str):
    """Parses an OCC option symbol into its components."""
    match = re.match(r'^([A-Z]{1,6})(\d{6})([CP])(\d{8})$', occ_symbol)
    if match:
        root = match.group(1)
        exp = match.group(2)
        opt_type = match.group(3)
        strike = float(match.group(4)) / 1000.0
        return root, exp, opt_type, strike
    return None

def calculate_portfolio_economics(positions) -> Dict[str, Any]:
    """
    Takes a list of Alpaca Position objects (or dicts) and returns 
    the total exposure, total risk, and grouped strategies.
    
    Alpaca's cost_basis for shorts is negative. 
    Net debit/credit is calculated by summing the cost bases.
    """
    groups = defaultdict(list)
    
    # 1. Group positions by underlying, expiration, and option type
    for p in positions:
        # Support both Alpaca Position objects and dictionaries (for testing)
        symbol = getattr(p, 'symbol', p.get('symbol') if isinstance(p, dict) else None)
        qty = float(getattr(p, 'qty', p.get('qty', 0) if isinstance(p, dict) else 0))
        cost_basis = float(getattr(p, 'cost_basis', p.get('cost_basis', 0) if isinstance(p, dict) else 0))
        
        parsed = parse_occ(symbol)
        if not parsed:
            # Not an option, or invalid. Treat independently.
            groups[('UNKNOWN', symbol, 'UNKNOWN')].append({
                'symbol': symbol,
                'qty': qty,
                'cost_basis': cost_basis,
                'strike': 0.0
            })
            continue
            
        root, exp, opt_type, strike = parsed
        groups[(root, exp, opt_type)].append({
            'symbol': symbol,
            'qty': qty,
            'cost_basis': cost_basis,
            'strike': strike
        })
        
    strategies = []
    
    # 2. Pair legs into strategies
    for (root, exp, opt_type), legs in groups.items():
        if root == 'UNKNOWN':
            for leg in legs:
                strategies.append({
                    "strategy_type": "NakedEquity",
                    "legs": [leg],
                    "net_cost": leg['cost_basis'],
                    "max_loss": abs(leg['cost_basis']),
                    "capital_requirement": abs(leg['cost_basis'])
                })
            continue

        longs = sorted([l for l in legs if l['qty'] > 0], key=lambda x: x['strike'])
        shorts = sorted([l for l in legs if l['qty'] < 0], key=lambda x: x['strike'])
        
        # Pass 1: Quantity-based exact match disambiguation
        # Group remaining legs by abs(qty)
        def pair_strategies_by_pass(long_pool, short_pool):
            longs_by_qty = defaultdict(list)
            shorts_by_qty = defaultdict(list)
            for l in long_pool: longs_by_qty[l['qty']].append(l)
            for s in short_pool: shorts_by_qty[abs(s['qty'])].append(s)
            
            matched_longs = []
            matched_shorts = []
            
            for qty, l_list in longs_by_qty.items():
                s_list = shorts_by_qty.get(qty, [])
                if len(l_list) == 1 and len(s_list) == 1:
                    # Exactly one long and one short of this quantity
                    l = l_list[0]
                    s = s_list[0]
                    matched_longs.append(l)
                    matched_shorts.append(s)
                    
                    net_cost = l['cost_basis'] + s['cost_basis']
                    strike_width = abs(l['strike'] - s['strike'])
                    
                    if opt_type == 'C':
                        strat_type = "BullCallSpread" if l['strike'] < s['strike'] else "BearCallSpread"
                    else:
                        strat_type = "BearPutSpread" if l['strike'] > s['strike'] else "BullPutSpread"
                        
                    if net_cost > 0:
                        max_loss = net_cost
                        cap_req = net_cost
                    else:
                        max_loss = (strike_width * 100 * qty) - abs(net_cost)
                        cap_req = max_loss
                        
                    strategies.append({
                        "strategy_type": strat_type,
                        "legs": [
                            {"symbol": l['symbol'], "qty": qty, "strike": l['strike'], "cost_basis": l['cost_basis']},
                            {"symbol": s['symbol'], "qty": -qty, "strike": s['strike'], "cost_basis": s['cost_basis']}
                        ],
                        "net_cost": net_cost,
                        "max_loss": max_loss,
                        "capital_requirement": cap_req
                    })
            
            # Remove matched from pools
            return [l for l in long_pool if l not in matched_longs], [s for s in short_pool if s not in matched_shorts]
            
        longs, shorts = pair_strategies_by_pass(longs, shorts)
        
        # Pass 2: Single-leg fallback match
        # If exactly 1 long and 1 short remaining, we pair them up to the min quantity
        if len(longs) == 1 and len(shorts) == 1:
            l = longs[0]
            s = shorts[0]
            match_qty = min(l['qty'], abs(s['qty']))
            
            l_cost_matched = l['cost_basis'] * (match_qty / l['qty'])
            s_cost_matched = s['cost_basis'] * (match_qty / abs(s['qty']))
            net_cost = l_cost_matched + s_cost_matched
            strike_width = abs(l['strike'] - s['strike'])
            
            if opt_type == 'C':
                strat_type = "BullCallSpread" if l['strike'] < s['strike'] else "BearCallSpread"
            else:
                strat_type = "BearPutSpread" if l['strike'] > s['strike'] else "BullPutSpread"
                
            if net_cost > 0:
                max_loss = net_cost
                cap_req = net_cost
            else:
                max_loss = (strike_width * 100 * match_qty) - abs(net_cost)
                cap_req = max_loss
                
            strategies.append({
                "strategy_type": strat_type,
                "legs": [
                    {"symbol": l['symbol'], "qty": match_qty, "strike": l['strike'], "cost_basis": l_cost_matched},
                    {"symbol": s['symbol'], "qty": -match_qty, "strike": s['strike'], "cost_basis": s_cost_matched}
                ],
                "net_cost": net_cost,
                "max_loss": max_loss,
                "capital_requirement": cap_req
            })
            
            l['qty'] -= match_qty
            l['cost_basis'] -= l_cost_matched
            s['qty'] += match_qty
            s['cost_basis'] -= s_cost_matched
            
        # Pass 3: Ambiguity rejection
        # Any remaining legs (including remainders from Pass 2, or multiple ambiguous legs) 
        # are strictly treated as independent to avoid dangerous guessing.
        for l in longs:
            if l['qty'] > 0:
                strat_type = "LongCall" if opt_type == 'C' else "LongPut"
                strategies.append({
                    "strategy_type": strat_type,
                    "legs": [{"symbol": l['symbol'], "qty": l['qty'], "strike": l['strike'], "cost_basis": l['cost_basis']}],
                    "net_cost": l['cost_basis'],
                    "max_loss": l['cost_basis'],
                    "capital_requirement": l['cost_basis']
                })
        for s in shorts:
            if s['qty'] < 0:
                strat_type = "ShortCall" if opt_type == 'C' else "ShortPut"
                strategies.append({
                    "strategy_type": strat_type,
                    "legs": [{"symbol": s['symbol'], "qty": s['qty'], "strike": s['strike'], "cost_basis": s['cost_basis']}],
                    "net_cost": s['cost_basis'],
                    "max_loss": float('inf'),
                    "capital_requirement": abs(s['cost_basis']) 
                })

                
    total_exposure = sum(s['capital_requirement'] for s in strategies)
    total_risk = sum(s['max_loss'] for s in strategies if s['max_loss'] != float('inf'))
    
    return {
        "total_exposure": total_exposure,
        "total_risk": total_risk,
        "open_positions_count": len(strategies),
        "strategies": strategies
    }
