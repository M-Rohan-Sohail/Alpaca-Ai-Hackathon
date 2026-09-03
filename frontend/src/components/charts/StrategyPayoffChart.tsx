"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatCurrency } from "@/lib/utils";
import type { OptionLeg } from "@/lib/api/types";

// Visual-only hockey-stick chart. It draws a piecewise-linear curve through
// the backend-provided anchor points (strikes, breakevens, max loss/profit)
// -- it never derives, prices, or recomputes options economics itself
// (Section C: "frontend must NEVER compute options math").

function buildPayoffPoints(
  legs: OptionLeg[],
  maxLoss: number,
  maxProfit: number,
  breakeven: number[],
  strategyType: string,
) {
  if (legs.length === 0 || breakeven.length === 0) return [];

  const strikes = [...new Set(legs.map((l) => l.strike))].sort((a, b) => a - b);
  const lowStrike = strikes[0];
  const highStrike = strikes[strikes.length - 1];
  const span = Math.max(highStrike - lowStrike, 1) * 1.5;
  const rangeLow = Math.max(0, lowStrike - span);
  const rangeHigh = highStrike + span;

  const isBearish = /bear/i.test(strategyType);

  if (breakeven.length === 1) {
    const be = breakeven[0];
    const leftVal = isBearish ? maxProfit : -maxLoss;
    const rightVal = isBearish ? -maxLoss : maxProfit;
    return [
      { price: rangeLow, pnl: leftVal },
      { price: lowStrike, pnl: leftVal },
      { price: be, pnl: 0 },
      { price: highStrike, pnl: rightVal },
      { price: rangeHigh, pnl: rightVal },
    ];
  }

  const [beLow, beHigh] = [Math.min(...breakeven), Math.max(...breakeven)];
  return [
    { price: rangeLow, pnl: -maxLoss },
    { price: beLow, pnl: 0 },
    { price: (beLow + beHigh) / 2, pnl: maxProfit },
    { price: beHigh, pnl: 0 },
    { price: rangeHigh, pnl: -maxLoss },
  ];
}

export function StrategyPayoffChart({
  legs,
  maxLoss,
  maxProfit,
  breakeven,
  strategyType,
}: {
  legs: OptionLeg[];
  maxLoss: number | null;
  maxProfit: number | null;
  breakeven: number[];
  strategyType: string;
}) {
  if (maxLoss == null || maxProfit == null || breakeven.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center rounded-md border border-dashed border-border text-xs text-subtle-foreground">
        Payoff data not available.
      </div>
    );
  }

  const points = buildPayoffPoints(
    legs,
    maxLoss,
    maxProfit,
    breakeven,
    strategyType,
  );

  return (
    <div className="h-48 w-full rounded-md border border-border bg-background p-2">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={points} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="payoffProfit" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--profit)" stopOpacity={0.35} />
              <stop offset="100%" stopColor="var(--profit)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis
            dataKey="price"
            type="number"
            domain={["dataMin", "dataMax"]}
            tick={{ fontSize: 10, fill: "var(--subtle-foreground)" }}
            tickFormatter={(v: number) => v.toFixed(0)}
            stroke="var(--border-strong)"
          />
          <YAxis
            tick={{ fontSize: 10, fill: "var(--subtle-foreground)" }}
            tickFormatter={(v: number) => formatCurrency(v)}
            stroke="var(--border-strong)"
            width={64}
          />
          <ReferenceLine y={0} stroke="var(--border-strong)" />
          {breakeven.map((be, i) => (
            <ReferenceLine
              key={i}
              x={be}
              stroke="var(--info)"
              strokeDasharray="4 4"
              label={{
                value: `BE ${be.toFixed(2)}`,
                fontSize: 10,
                fill: "var(--info)",
                position: "top",
              }}
            />
          ))}
          <Tooltip
            contentStyle={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: 6,
              fontSize: 12,
            }}
            labelFormatter={(v) => `Underlying: ${Number(v).toFixed(2)}`}
            formatter={(value) => [formatCurrency(Number(value)), "P&L"]}
          />
          <Area
            type="linear"
            dataKey="pnl"
            stroke="var(--foreground)"
            strokeWidth={1.5}
            fill="url(#payoffProfit)"
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
