"use client";

import Link from "next/link";
import {
  Wallet,
  Landmark,
  TrendingDown,
  Layers,
  ArrowUpRight,
} from "lucide-react";
import { useDashboard, usePositions } from "@/lib/api/hooks";
import { KpiCard } from "@/components/ui/KpiCard";
import { RiskMeter } from "@/components/ui/RiskMeter";
import { PnlBadge } from "@/components/ui/PnlBadge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import {
  EmptyState,
  ErrorState,
  LoadingSkeleton,
  StaleDataBanner,
} from "@/components/ui/States";
import { formatCurrency, formatRelativeTime, isStale } from "@/lib/utils";
import type { ActivityEvent, ExitStatus } from "@/lib/api/types";

const ACTIVITY_TONE: Record<ActivityEvent["type"], "profit" | "loss" | "info" | "warning" | "neutral"> = {
  TRADE: "info",
  REJECT: "loss",
  EXIT: "profit",
  FILL: "profit",
  SYSTEM: "neutral",
};

const EXIT_STATUS_TONE: Record<ExitStatus, "info" | "warning" | "neutral"> = {
  HOLDING: "info",
  PENDING_EXIT: "warning",
  CLOSED: "neutral",
};

export default function DashboardPage() {
  const { data: dashboard, isLoading, isError } = useDashboard();
  const { data: positions } = usePositions();

  if (isLoading) return <LoadingSkeleton rows={5} />;
  if (isError || !dashboard)
    return <ErrorState message="Failed to load dashboard data." />;

  const dailyLossPct =
    dashboard.daily_loss_used != null && dashboard.daily_loss_limit
      ? (dashboard.daily_loss_used / dashboard.daily_loss_limit) * 100
      : null;

  return (
    <div className="flex flex-col gap-4">
      {isStale(dashboard.updated_at) && <StaleDataBanner />}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard
          label="Account Equity"
          value={formatCurrency(dashboard.equity)}
          icon={Wallet}
        />
        <KpiCard
          label="Buying Power"
          value={formatCurrency(dashboard.buying_power)}
          icon={Landmark}
        />
        <KpiCard
          label="Daily Loss Used"
          value={formatCurrency(dashboard.daily_loss_used)}
          subValue={
            dashboard.daily_loss_limit != null
              ? `Limit: ${formatCurrency(dashboard.daily_loss_limit)}`
              : undefined
          }
          icon={TrendingDown}
          progress={dailyLossPct}
          progressTone={
            dailyLossPct != null && dailyLossPct >= 90
              ? "loss"
              : dailyLossPct != null && dailyLossPct >= 70
                ? "warning"
                : "info"
          }
        />
        <KpiCard
          label="Open Positions"
          value={`${dashboard.open_positions ?? "N/A"} / ${dashboard.max_positions ?? "N/A"}`}
          icon={Layers}
          progress={
            dashboard.open_positions != null && dashboard.max_positions
              ? (dashboard.open_positions / dashboard.max_positions) * 100
              : null
          }
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-border bg-surface p-4">
          <h3 className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Pipeline Activity Feed
          </h3>
          {dashboard.recent_activity.length === 0 ? (
            <EmptyState message="No recent pipeline activity." />
          ) : (
            <ul className="flex flex-col gap-2.5">
              {dashboard.recent_activity.map((event) => (
                <li
                  key={event.id}
                  className="flex items-start justify-between gap-3 border-b border-border pb-2.5 last:border-0 last:pb-0"
                >
                  <div className="flex items-start gap-2">
                    <StatusBadge
                      label={event.type}
                      tone={ACTIVITY_TONE[event.type]}
                      className="mt-0.5"
                    />
                    <span className="text-sm text-foreground">
                      {event.message}
                    </span>
                  </div>
                  <span className="shrink-0 whitespace-nowrap text-xs text-subtle-foreground">
                    {formatRelativeTime(event.timestamp)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-lg border border-border bg-surface p-4">
          <h3 className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Risk Utilization
          </h3>
          <div className="flex flex-col gap-4">
            <RiskMeter
              label="Exposure Capacity"
              used={dashboard.exposure_used}
              limit={dashboard.exposure_limit}
            />
            <RiskMeter
              label="Daily Loss Capacity"
              used={dashboard.daily_loss_used}
              limit={dashboard.daily_loss_limit}
            />
            <div className="flex items-center justify-between rounded-md border border-border bg-background px-3 py-2 text-xs">
              <span className="text-muted-foreground">Open Position Capacity</span>
              <span className="font-mono text-foreground">
                {dashboard.open_positions ?? "N/A"} / {dashboard.max_positions ?? "N/A"}
              </span>
            </div>
            <Link
              href="/risk-dashboard"
              className="flex items-center gap-1 text-xs text-info hover:underline"
            >
              View full Risk Dashboard <ArrowUpRight className="h-3 w-3" />
            </Link>
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-border bg-surface p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Active Positions
          </h3>
          <Link
            href="/positions"
            className="flex items-center gap-1 text-xs text-info hover:underline"
          >
            View all <ArrowUpRight className="h-3 w-3" />
          </Link>
        </div>
        {!positions || positions.length === 0 ? (
          <EmptyState message="No active positions." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[600px] text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-muted-foreground">
                  <th className="px-2 py-2 font-medium">Symbol</th>
                  <th className="px-2 py-2 font-medium">Strategy</th>
                  <th className="px-2 py-2 font-medium text-right">Unrealized P&L</th>
                  <th className="px-2 py-2 font-medium text-right">Return %</th>
                  <th className="px-2 py-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {positions.slice(0, 5).map((pos) => (
                  <tr
                    key={pos.strategy_id}
                    className="border-b border-border last:border-0"
                  >
                    <td className="px-2 py-2.5 font-mono font-semibold text-foreground">
                      {pos.symbol}
                    </td>
                    <td className="px-2 py-2.5 text-muted-foreground whitespace-nowrap">
                      {pos.strategy_type}
                    </td>
                    <td className="px-2 py-2.5 text-right">
                      <PnlBadge value={pos.unrealized_pnl} variant="currency" />
                    </td>
                    <td className="px-2 py-2.5 text-right">
                      <PnlBadge value={pos.return_pct} variant="percent" />
                    </td>
                    <td className="px-2 py-2.5">
                      <StatusBadge
                        label={pos.exit_status}
                        tone={EXIT_STATUS_TONE[pos.exit_status]}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
