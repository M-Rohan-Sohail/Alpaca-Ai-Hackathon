"use client";

import { useDashboard, usePipelineLatest } from "@/lib/api/hooks";
import { RiskMeter } from "@/components/ui/RiskMeter";
import { RiskAssessmentCard } from "@/components/pipeline/RiskAssessmentCard";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui/States";
import { formatCurrency } from "@/lib/utils";

export default function RiskDashboardPage() {
  const { data: dashboard, isLoading: dashboardLoading, isError: dashboardError } =
    useDashboard();
  const { data: candidates, isLoading: pipelineLoading } = usePipelineLatest();

  if (dashboardLoading || pipelineLoading) return <LoadingSkeleton rows={6} />;
  if (dashboardError || !dashboard)
    return <ErrorState message="Failed to load risk dashboard." />;

  const latestEvaluated = (candidates ?? []).find(
    (c) => c.evaluations.length > 0,
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-lg border border-border bg-surface p-4">
        <h3 className="mb-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Account-Wide Risk Capacity
        </h3>
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
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
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Buying Power Capacity</span>
              <span className="font-mono text-foreground tabular-nums">
                {formatCurrency(dashboard.buying_power)} available
              </span>
            </div>
            <div className="h-2 w-full rounded-full bg-border" />
          </div>
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Open Position Capacity</span>
              <span className="font-mono text-foreground tabular-nums">
                {dashboard.open_positions ?? "N/A"} / {dashboard.max_positions ?? "N/A"}
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-border">
              <div
                className="h-full rounded-full bg-info transition-all"
                style={{
                  width:
                    dashboard.open_positions != null && dashboard.max_positions
                      ? `${Math.min(100, (dashboard.open_positions / dashboard.max_positions) * 100)}%`
                      : "0%",
                }}
              />
            </div>
          </div>
        </div>
      </div>

      <div>
        <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Most Recent Risk Engine Decision
          {latestEvaluated && (
            <span className="ml-2 font-mono text-foreground normal-case">
              ({latestEvaluated.symbol})
            </span>
          )}
        </h3>
        <p className="mb-3 text-xs text-subtle-foreground">
          Per-Trade, Exposure, Account Risk, Daily Loss, Buying Power, and Open
          Position capacity checks performed for the last candidate evaluated
          by the Risk Engine. The Risk Engine is the absolute authority: its
          ACCEPT/REJECT decision cannot be overridden from this client.
        </p>
        {latestEvaluated ? (
          <RiskAssessmentCard evaluation={latestEvaluated.evaluations[0]} />
        ) : (
          <EmptyState message="No candidates have reached the Risk Engine yet." />
        )}
      </div>
    </div>
  );
}
