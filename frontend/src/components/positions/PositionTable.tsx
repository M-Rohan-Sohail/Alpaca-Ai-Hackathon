"use client";

import { Fragment, useState } from "react";
import { ChevronDown, X } from "lucide-react";
import { cn, formatCurrency, formatNumber } from "@/lib/utils";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { PnlBadge } from "@/components/ui/PnlBadge";
import { ExpandableLegTable } from "@/components/positions/ExpandableLegTable";
import type { ExitStatus, Position } from "@/lib/api/types";

const EXIT_STATUS_TONE: Record<ExitStatus, "info" | "warning" | "neutral"> = {
  HOLDING: "info",
  PENDING_EXIT: "warning",
  CLOSED: "neutral",
};

export function PositionTable({
  positions,
  onRequestClose,
}: {
  positions: Position[];
  onRequestClose: (position: Position) => void;
}) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  function toggle(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-surface">
      <table className="w-full min-w-[1100px] text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs text-muted-foreground">
            <th className="w-8 px-3 py-2.5" />
            <th className="px-3 py-2.5 font-medium">Symbol</th>
            <th className="px-3 py-2.5 font-medium">Strategy</th>
            <th className="px-3 py-2.5 font-medium text-right">Qty</th>
            <th className="px-3 py-2.5 font-medium text-right">Entry</th>
            <th className="px-3 py-2.5 font-medium text-right">Current</th>
            <th className="px-3 py-2.5 font-medium text-right">Unrealized P&L</th>
            <th className="px-3 py-2.5 font-medium text-right">Return %</th>
            <th className="px-3 py-2.5 font-medium text-right">Max Loss</th>
            <th className="px-3 py-2.5 font-medium text-right">Max Profit</th>
            <th className="px-3 py-2.5 font-medium text-right">Breakeven</th>
            <th className="px-3 py-2.5 font-medium text-right">DTE</th>
            <th className="px-3 py-2.5 font-medium text-right">Days Held</th>
            <th className="px-3 py-2.5 font-medium">Exit Status</th>
            <th className="px-3 py-2.5 font-medium text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((pos) => {
            const isOpen = expanded.has(pos.strategy_id);
            return (
              <Fragment key={pos.strategy_id}>
                <tr
                  className="border-b border-border last:border-0 hover:bg-surface-hover cursor-pointer"
                  onClick={() => toggle(pos.strategy_id)}
                >
                  <td className="px-3 py-3">
                    <ChevronDown
                      className={cn(
                        "h-4 w-4 text-subtle-foreground transition-transform",
                        isOpen && "rotate-180",
                      )}
                    />
                  </td>
                  <td className="px-3 py-3 font-mono font-semibold text-foreground">
                    {pos.symbol}
                  </td>
                  <td className="px-3 py-3 text-muted-foreground whitespace-nowrap">
                    {pos.strategy_type}
                  </td>
                  <td className="px-3 py-3 text-right font-mono tabular-nums">
                    {formatNumber(pos.quantity)}
                  </td>
                  <td className="px-3 py-3 text-right font-mono tabular-nums">
                    {formatCurrency(pos.entry_price)}
                  </td>
                  <td className="px-3 py-3 text-right font-mono tabular-nums">
                    {formatCurrency(pos.current_value)}
                  </td>
                  <td className="px-3 py-3 text-right">
                    <PnlBadge value={pos.unrealized_pnl} variant="currency" />
                  </td>
                  <td className="px-3 py-3 text-right">
                    <PnlBadge value={pos.return_pct} variant="percent" />
                  </td>
                  <td className="px-3 py-3 text-right font-mono tabular-nums text-loss">
                    {formatCurrency(pos.max_loss)}
                  </td>
                  <td className="px-3 py-3 text-right font-mono tabular-nums text-profit">
                    {formatCurrency(pos.max_profit)}
                  </td>
                  <td className="px-3 py-3 text-right font-mono tabular-nums text-muted-foreground">
                    {pos.breakeven.length > 0
                      ? pos.breakeven.map((b) => b.toFixed(2)).join(" / ")
                      : "N/A"}
                  </td>
                  <td className="px-3 py-3 text-right font-mono tabular-nums">
                    {pos.dte ?? "N/A"}
                  </td>
                  <td className="px-3 py-3 text-right font-mono tabular-nums">
                    {pos.days_held}
                  </td>
                  <td className="px-3 py-3">
                    <StatusBadge
                      label={pos.exit_status}
                      tone={EXIT_STATUS_TONE[pos.exit_status]}
                    />
                  </td>
                  <td className="px-3 py-3 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onRequestClose(pos);
                      }}
                      className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs text-muted-foreground hover:border-loss/40 hover:text-loss"
                    >
                      <X className="h-3 w-3" />
                      Force Close
                    </button>
                  </td>
                </tr>
                {isOpen && (
                  <tr className="border-b border-border last:border-0 bg-background/40">
                    <td colSpan={14} className="px-3 py-3">
                      <ExpandableLegTable
                        legs={pos.legs}
                        maxLoss={pos.max_loss}
                        maxProfit={pos.max_profit}
                        breakeven={pos.breakeven}
                        strategyType={pos.strategy_type}
                      />
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
