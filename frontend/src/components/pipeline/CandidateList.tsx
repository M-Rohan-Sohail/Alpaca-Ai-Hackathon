import { cn, formatRelativeTime } from "@/lib/utils";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { PipelineCandidate } from "@/lib/api/types";

function candidateOutcome(candidate: PipelineCandidate) {
  const evaluation = candidate.evaluations[0];
  const decision = candidate.decisions[0];

  if (evaluation) {
    return evaluation.decision === "REJECT"
      ? { label: "REJECTED", tone: "loss" as const }
      : { label: "ACCEPTED", tone: "profit" as const };
  }
  if (decision) {
    return decision.decision === "PASS"
      ? { label: "PASSED", tone: "neutral" as const }
      : { label: "IN RISK", tone: "info" as const };
  }
  if (!candidate.scores.filter_passed) {
    return { label: "FILTERED", tone: "neutral" as const };
  }
  return { label: "PROCESSING", tone: "warning" as const };
}

export function CandidateList({
  candidates,
  selectedSymbol,
  onSelect,
}: {
  candidates: PipelineCandidate[];
  selectedSymbol: string | null;
  onSelect: (symbol: string) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      {candidates.map((c) => {
        const outcome = candidateOutcome(c);
        const active = c.symbol === selectedSymbol;
        return (
          <button
            key={c.symbol}
            onClick={() => onSelect(c.symbol)}
            className={cn(
              "flex flex-col gap-1.5 rounded-md border px-3 py-2.5 text-left transition-colors",
              active
                ? "border-info bg-info-bg"
                : "border-border bg-surface hover:bg-surface-hover",
            )}
          >
            <div className="flex items-center justify-between">
              <span className="font-mono text-sm font-semibold text-foreground">
                {c.symbol}
              </span>
              <StatusBadge label={outcome.label} tone={outcome.tone} />
            </div>
            <div className="flex items-center justify-between text-xs text-subtle-foreground">
              <span>{c.strategy?.type ?? "No strategy yet"}</span>
              <span>{formatRelativeTime(c.updated_at)}</span>
            </div>
          </button>
        );
      })}
    </div>
  );
}
