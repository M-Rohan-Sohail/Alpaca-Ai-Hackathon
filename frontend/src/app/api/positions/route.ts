import { NextResponse } from "next/server";
import { positions } from "@/lib/mock/store";
import type { Position } from "@/lib/api/types";

// Simulates live Alpaca quote jitter on top of the stored entry economics,
// mirroring what the real backend would compute by combining Trade Journal
// entry prices with live market data (Section M.2). Purely cosmetic here.
function withJitter(pos: Position): Position {
  const drift = Math.sin(Date.now() / 4000 + pos.symbol.length) * 0.015;
  if (pos.current_value == null || pos.unrealized_pnl == null) return pos;
  const jitteredValue = Math.max(0.01, pos.current_value * (1 + drift));
  const perContractDelta = jitteredValue - pos.entry_price;
  const pnl = perContractDelta * pos.quantity * 100;
  const returnPct = (perContractDelta / pos.entry_price) * 100;
  return {
    ...pos,
    current_value: Number(jitteredValue.toFixed(2)),
    unrealized_pnl: Number(pnl.toFixed(2)),
    return_pct: Number(returnPct.toFixed(1)),
  };
}

export async function GET() {
  return NextResponse.json(positions.map(withJitter));
}
