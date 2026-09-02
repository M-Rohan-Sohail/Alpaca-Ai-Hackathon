"use client";

import { useState } from "react";
import {
  ChevronDown,
  Database,
  Newspaper,
  LineChart,
  Brain,
  Calculator,
  Rocket,
  Check,
  Ban,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { DecisionCard } from "@/components/pipeline/DecisionCard";
import { RiskAssessmentCard } from "@/components/pipeline/RiskAssessmentCard";
import { StrategyPayoffChart } from "@/components/charts/StrategyPayoffChart";
import type { PipelineCandidate } from "@/lib/api/types";

type StepStatus = "complete" | "active" | "pending" | "skipped" | "rejected";

function StepIcon({
  status,
  icon: Icon,
}: {
  status: StepStatus;
  icon: React.ElementType;
}) {
  const base =
    "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2";
  if (status === "rejected") {
    return (
      <div className={cn(base, "border-loss bg-loss-bg text-loss")}>
        <X className="h-4 w-4" />
      </div>
    );
  }
  if (status === "complete") {
    return (
      <div className={cn(base, "border-profit bg-profit-bg text-profit")}>
        <Check className="h-4 w-4" />
      </div>
    );
  }
  if (status === "active") {
    return (
      <div className={cn(base, "border-info bg-info-bg text-info animate-pulse")}>
        <Icon className="h-4 w-4" />
      </div>
    );
  }
  if (status === "skipped") {
    return (
      <div className={cn(base, "border-border-strong bg-surface text-subtle-foreground")}>
        <Ban className="h-4 w-4" />
      </div>
    );
  }
  return (
    <div className={cn(base, "border-border bg-surface text-subtle-foreground")}>
      <Icon className="h-4 w-4" />
    </div>
  );
}

export function PipelineStepper({
  candidate,
}: {
  candidate: PipelineCandidate;
}) {
  const hasMarketNews = candidate.analysis.direction != null;
  const hasOptions = candidate.strategy != null;
  const hasDecision = candidate.decisions.length > 0;
  const decisionIsPass = candidate.decisions[0]?.decision === "PASS";
  const hasRisk = candidate.evaluations.length > 0;
  const riskIsReject = candidate.evaluations[0]?.decision === "REJECT";
  const hasExecution = candidate.execution.status !== "NOT_SUBMITTED";

  const stopped = decisionIsPass || riskIsReject;

  const steps: Array<{
    key: string;
    title: string;
    icon: React.ElementType;
    status: StepStatus;
    content: React.ReactNode;
  }> = [
    {
      key: "data",
      title: "1. Data Processing",
      icon: Database,
      status: "complete",
      content: (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Metric label="Trend Score" value={candidate.scores.trend} />
          <Metric label="Momentum" value={candidate.scores.momentum} />
          <Metric label="Volume" value={candidate.scores.volume} />
          <div>
            <div className="text-xs text-muted-foreground">Filter Result</div>
            <StatusBadge
              className="mt-1"
              label={candidate.scores.filter_passed ? "PASSED" : "FILTERED OUT"}
              tone={candidate.scores.filter_passed ? "profit" : "loss"}
            />
          </div>
        </div>
      ),
    },
    {
      key: "market_news",
      title: "2. Market & News Agent",
      icon: Newspaper,
      status: hasMarketNews ? "complete" : "pending",
      content: hasMarketNews ? (
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <div className="text-xs text-muted-foreground">
                AI Directional Bias
              </div>
              <StatusBadge
                className="mt-1"
                label={candidate.analysis.direction ?? "N/A"}
                tone={
                  candidate.analysis.direction === "BULLISH"
                    ? "profit"
                    : candidate.analysis.direction === "BEARISH"
                      ? "loss"
                      : "neutral"
                }
              />
            </div>
            <div>
              <div className="text-xs text-muted-foreground">
                News Sentiment (Python Score)
              </div>
              <div className="mt-1 flex items-center gap-2">
                <StatusBadge
                  label={candidate.news.sentiment ?? "N/A"}
                  tone={
                    candidate.news.sentiment === "POSITIVE"
                      ? "profit"
                      : candidate.news.sentiment === "NEGATIVE"
                        ? "loss"
                        : "neutral"
                  }
                />
                <span className="font-mono text-xs text-muted-foreground">
                  {candidate.news.news_score?.toFixed(2) ?? "N/A"}
                </span>
              </div>
            </div>
          </div>
          {candidate.analysis.summary && (
            <p className="text-sm text-muted-foreground">
              {candidate.analysis.summary}
            </p>
          )}
          {candidate.news.headlines.length > 0 && (
            <ul className="flex flex-col gap-1">
              {candidate.news.headlines.map((h, i) => (
                <li key={i} className="text-xs text-subtle-foreground">
                  · {h}
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : (
        <PendingNote />
      ),
    },
    {
      key: "options",
      title: "3. Options Agent",
      icon: LineChart,
      status: hasOptions ? "complete" : "pending",
      content: hasOptions ? (
        <div className="flex flex-col gap-3">
          <div className="text-sm font-medium text-foreground">
            {candidate.strategy!.type}
          </div>
          <div className="overflow-x-auto rounded-md border border-border">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border bg-background text-muted-foreground">
                  <th className="px-2 py-1.5 text-left font-medium">Side</th>
                  <th className="px-2 py-1.5 text-left font-medium">Type</th>
                  <th className="px-2 py-1.5 text-left font-medium">Strike</th>
                  <th className="px-2 py-1.5 text-left font-medium">Exp</th>
                  <th className="px-2 py-1.5 text-left font-medium">OCC Symbol</th>
                </tr>
              </thead>
              <tbody className="font-mono">
                {candidate.strategy!.legs.map((leg, i) => (
                  <tr key={i} className="border-b border-border last:border-0">
                    <td
                      className={cn(
                        "px-2 py-1.5 font-semibold",
                        leg.side === "BUY" ? "text-profit" : "text-loss",
                      )}
                    >
                      {leg.side}
                    </td>
                    <td className="px-2 py-1.5">{leg.option_type}</td>
                    <td className="px-2 py-1.5">{leg.strike}</td>
                    <td className="px-2 py-1.5">{leg.expiration}</td>
                    <td className="px-2 py-1.5 text-subtle-foreground">
                      {leg.occ_symbol}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <StrategyPayoffChart
            legs={candidate.strategy!.legs}
            maxLoss={candidate.strategy!.max_loss}
            maxProfit={candidate.strategy!.max_profit}
            breakeven={candidate.strategy!.breakeven}
            strategyType={candidate.strategy!.type ?? ""}
          />
        </div>
      ) : (
        <PendingNote />
      ),
    },
    {
      key: "decision",
      title: "4. Decision Agent (AI / Qualitative)",
      icon: Brain,
      status: hasDecision ? "complete" : "pending",
      content: hasDecision ? (
        <DecisionCard decision={candidate.decisions[0]} />
      ) : (
        <PendingNote />
      ),
    },
    {
      key: "risk",
      title: "5. Risk Engine (Deterministic / Authority)",
      icon: Calculator,
      status: !hasDecision
        ? "pending"
        : decisionIsPass
          ? "skipped"
          : hasRisk
            ? riskIsReject
              ? "rejected"
              : "complete"
            : "pending",
      content: decisionIsPass ? (
        <SkippedNote reason="Decision Agent passed; trade was never submitted for risk sizing." />
      ) : hasRisk ? (
        <RiskAssessmentCard evaluation={candidate.evaluations[0]} />
      ) : (
        <PendingNote />
      ),
    },
    {
      key: "execution",
      title: "6. Execution",
      icon: Rocket,
      status: stopped
        ? "skipped"
        : hasExecution
          ? "complete"
          : hasRisk
            ? "pending"
            : "pending",
      content: stopped ? (
        <SkippedNote
          reason={
            riskIsReject
              ? "Trade rejected by Risk Engine; no order was submitted."
              : "Decision Agent passed; no order was submitted."
          }
        />
      ) : hasExecution ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <div>
            <div className="text-xs text-muted-foreground">Status</div>
            <StatusBadge
              className="mt-1"
              label={candidate.execution.status}
              tone={candidate.execution.status === "FILLED" ? "profit" : "info"}
            />
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Order ID</div>
            <div className="mt-1 font-mono text-xs text-foreground">
              {candidate.execution.order_id ?? "N/A"}
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Filled At</div>
            <div className="mt-1 font-mono text-xs text-foreground">
              {candidate.execution.filled_at
                ? new Date(candidate.execution.filled_at).toLocaleTimeString()
                : "N/A"}
            </div>
          </div>
        </div>
      ) : (
        <PendingNote />
      ),
    },
  ];

  const defaultExpanded = (() => {
    for (let i = steps.length - 1; i >= 0; i--) {
      if (steps[i].status !== "pending") return i;
    }
    return 0;
  })();

  const [expanded, setExpanded] = useState<number>(defaultExpanded);

  return (
    <div className="flex flex-col">
      {steps.map((step, i) => {
        const isOpen = expanded === i;
        const isLast = i === steps.length - 1;
        return (
          <div key={step.key} className="flex gap-3">
            <div className="flex flex-col items-center">
              <StepIcon status={step.status} icon={step.icon} />
              {!isLast && (
                <div
                  className={cn(
                    "w-0.5 flex-1 min-h-6",
                    step.status === "complete" || step.status === "rejected"
                      ? "bg-border-strong"
                      : "bg-border",
                  )}
                />
              )}
            </div>
            <div className="flex-1 pb-4">
              <button
                onClick={() => setExpanded(isOpen ? -1 : i)}
                className={cn(
                  "flex w-full items-center justify-between rounded-md border border-border bg-surface px-3 py-2.5 text-left transition-colors hover:bg-surface-hover",
                  step.status === "rejected" && "border-loss/40",
                )}
              >
                <span
                  className={cn(
                    "text-sm font-medium",
                    step.status === "pending"
                      ? "text-subtle-foreground"
                      : step.status === "rejected"
                        ? "text-loss"
                        : "text-foreground",
                  )}
                >
                  {step.title}
                </span>
                <ChevronDown
                  className={cn(
                    "h-4 w-4 shrink-0 text-subtle-foreground transition-transform",
                    isOpen && "rotate-180",
                  )}
                />
              </button>
              {isOpen && <div className="mt-2 px-1">{step.content}</div>}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number | null }) {
  return (
    <div>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="font-mono text-sm font-semibold text-foreground">
        {value != null ? value.toFixed(2) : "N/A"}
      </div>
    </div>
  );
}

function PendingNote() {
  return (
    <div className="rounded-md border border-dashed border-border px-3 py-3 text-xs text-subtle-foreground">
      Awaiting output from this stage.
    </div>
  );
}

function SkippedNote({ reason }: { reason: string }) {
  return (
    <div className="rounded-md border border-border bg-background px-3 py-3 text-xs text-muted-foreground">
      {reason}
    </div>
  );
}
