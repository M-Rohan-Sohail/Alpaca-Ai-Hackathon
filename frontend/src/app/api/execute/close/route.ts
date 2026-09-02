import { NextResponse } from "next/server";
import { closePosition } from "@/lib/mock/store";
import type { CloseTradeRequest, CloseTradeResponse } from "@/lib/api/types";

// Mirrors POST /api/execute/close (Section F). In production this routes
// into the Execution Agent's BUY_TO_CLOSE/SELL_TO_CLOSE logic; the frontend
// only ever triggers it after explicit user confirmation (Section J: Manual Close).
export async function POST(request: Request) {
  const body = (await request.json()) as CloseTradeRequest;

  if (!body?.strategy_id) {
    return NextResponse.json(
      { message: "strategy_id is required" },
      { status: 400 },
    );
  }

  const closed = closePosition(body.strategy_id);

  if (!closed) {
    const response: CloseTradeResponse = {
      strategy_id: body.strategy_id,
      status: "FAILED",
      message: "Position not found or already closed.",
    };
    return NextResponse.json(response, { status: 404 });
  }

  const response: CloseTradeResponse = {
    strategy_id: closed.strategy_id,
    status: "SUBMITTED",
    message: `Close order submitted for ${closed.symbol} ${closed.strategy_type}.`,
  };
  return NextResponse.json(response);
}
