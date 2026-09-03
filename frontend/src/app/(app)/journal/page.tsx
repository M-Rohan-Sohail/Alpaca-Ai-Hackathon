"use client";

import { useMemo, useState } from "react";
import { useJournal } from "@/lib/api/hooks";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui/States";
import { PnlBadge } from "@/components/ui/PnlBadge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { cn, formatCurrency, formatDateTime, formatNumber } from "@/lib/utils";

export default function JournalPage() {
  const { data: journal, isLoading, isError } = useJournal();

  const [symbol, setSymbol] = useState("");
  const [strategy, setStrategy] = useState("ALL");
  const [status, setStatus] = useState<"ALL" | "OPEN" | "CLOSED">("ALL");
  const [exitReason, setExitReason] = useState("ALL");

  const strategies = useMemo(
    () => Array.from(new Set((journal ?? []).map((j) => j.strategy_type))),
    [journal],
  );
  const exitReasons = useMemo(
    () =>
      Array.from(
        new Set((journal ?? []).map((j) => j.exit_reason).filter(Boolean)),
      ) as string[],
    [journal],
  );

  const filtered = useMemo(() => {
    if (!journal) return [];
    return journal.filter((j) => {
      if (symbol && !j.symbol.toLowerCase().includes(symbol.toLowerCase()))
        return false;
      if (strategy !== "ALL" && j.strategy_type !== strategy) return false;
      if (status !== "ALL" && j.status !== status) return false;
      if (exitReason !== "ALL" && j.exit_reason !== exitReason) return false;
      return true;
    });
  }, [journal, symbol, strategy, status, exitReason]);

  if (isLoading) return <LoadingSkeleton rows={6} />;
  if (isError) return <ErrorState message="Failed to load trade journal." />;
  if (!journal || journal.length === 0) {
    return <EmptyState message="No closed trades yet." />;
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-surface p-3">
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          placeholder="Filter symbol..."
          className="w-36 rounded-md border border-border bg-background px-2.5 py-1.5 text-sm text-foreground placeholder:text-subtle-foreground focus:outline-none focus:ring-1 focus:ring-info"
        />
        <Select value={strategy} onChange={setStrategy} label="Strategy">
          <option value="ALL">All Strategies</option>
          {strategies.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </Select>
        <Select
          value={status}
          onChange={(v) => setStatus(v as "ALL" | "OPEN" | "CLOSED")}
          label="Status"
        >
          <option value="ALL">All Status</option>
          <option value="OPEN">Open</option>
          <option value="CLOSED">Closed</option>
        </Select>
        <Select value={exitReason} onChange={setExitReason} label="Exit Reason">
          <option value="ALL">All Exit Reasons</option>
          {exitReasons.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </Select>
        <span className="ml-auto text-xs text-subtle-foreground">
          {filtered.length} of {journal.length} trades
        </span>
      </div>

      {filtered.length === 0 ? (
        <EmptyState message="No trades match the selected filters." />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border bg-surface">
          <table className="w-full min-w-[1000px] text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted-foreground">
                <th className="px-3 py-2.5 font-medium">Strategy ID</th>
                <th className="px-3 py-2.5 font-medium">Symbol</th>
                <th className="px-3 py-2.5 font-medium">Strategy</th>
                <th className="px-3 py-2.5 font-medium">Entry Time</th>
                <th className="px-3 py-2.5 font-medium text-right">Entry Price</th>
                <th className="px-3 py-2.5 font-medium text-right">Qty</th>
                <th className="px-3 py-2.5 font-medium">Exit Time</th>
                <th className="px-3 py-2.5 font-medium text-right">Exit Price</th>
                <th className="px-3 py-2.5 font-medium text-right">Realized P&L</th>
                <th className="px-3 py-2.5 font-medium text-right">Return %</th>
                <th className="px-3 py-2.5 font-medium">Exit Reason</th>
                <th className="px-3 py-2.5 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((j) => (
                <tr
                  key={j.strategy_id}
                  className="border-b border-border last:border-0 hover:bg-surface-hover"
                >
                  <td className="px-3 py-3 font-mono text-xs text-subtle-foreground">
                    {j.strategy_id}
                  </td>
                  <td className="px-3 py-3 font-mono font-semibold text-foreground">
                    {j.symbol}
                  </td>
                  <td className="px-3 py-3 text-muted-foreground whitespace-nowrap">
                    {j.strategy_type}
                  </td>
                  <td className="px-3 py-3 font-mono text-xs text-muted-foreground whitespace-nowrap">
                    {formatDateTime(j.entry_time)}
                  </td>
                  <td className="px-3 py-3 text-right font-mono tabular-nums">
                    {formatCurrency(j.entry_price)}
                  </td>
                  <td className="px-3 py-3 text-right font-mono tabular-nums">
                    {formatNumber(j.quantity)}
                  </td>
                  <td className="px-3 py-3 font-mono text-xs text-muted-foreground whitespace-nowrap">
                    {formatDateTime(j.exit_time)}
                  </td>
                  <td className="px-3 py-3 text-right font-mono tabular-nums">
                    {formatCurrency(j.exit_price)}
                  </td>
                  <td className="px-3 py-3 text-right">
                    <PnlBadge value={j.realized_pnl} variant="currency" />
                  </td>
                  <td className="px-3 py-3 text-right">
                    <PnlBadge value={j.return_pct} variant="percent" />
                  </td>
                  <td className="px-3 py-3 text-xs text-muted-foreground whitespace-nowrap">
                    {j.exit_reason ?? "N/A"}
                  </td>
                  <td className="px-3 py-3">
                    <StatusBadge
                      label={j.status}
                      tone={j.status === "CLOSED" ? "neutral" : "info"}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Select({
  value,
  onChange,
  children,
  label,
}: {
  value: string;
  onChange: (v: string) => void;
  children: React.ReactNode;
  label: string;
}) {
  return (
    <select
      aria-label={label}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={cn(
        "rounded-md border border-border bg-background px-2.5 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-info",
      )}
    >
      {children}
    </select>
  );
}
