import json
import os

journal_path = "/home/rohaanloq69/Desktop/ALPACA_HACKATHON_L1_L2_Connected/SAVE-DATA-PER-AGENT/Trade-Journal-Output/trade_journal.json"
with open(journal_path, 'r') as f:
    journal = json.load(f)

for entry in journal:
    if entry.get("status") == "CLOSED" and "exit_price" in entry:
        filled_price = entry["exit_price"]
        qty = float(entry.get("quantity", 1))
        
        if entry.get("initial_debit", 0) > 0:
            current_close_value = abs(filled_price) * 100 
            pnl = current_close_value - entry["initial_debit"]
            entry["realized_pnl"] = pnl * qty
            entry["return_pct"] = (pnl / entry["initial_debit"]) * 100
        else:
            current_close_cost = abs(filled_price) * 100
            pnl = entry.get("initial_credit", 0) - current_close_cost
            entry["realized_pnl"] = pnl * qty
            entry["return_pct"] = (pnl / entry.get("initial_credit", 1)) * 100

with open(journal_path, 'w') as f:
    json.dump(journal, f, indent=2)
print("Trade journal fixed!")
