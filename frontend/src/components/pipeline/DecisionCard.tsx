import { Brain } from "lucide-react";
import { cn } from "@/lib/utils";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { PipelineCandidate } from "@/lib/api/types";

export function DecisionCard({
  decision,
}: {
  decision: PipelineCandidate["decisions"][number] | undefined;
}) {
  if (!decision) {
    return (
      <div className="rounded-lg border border-dashed border-border p-4 text-sm text-subtle-foreground">
        Awaiting Decision Agent output.
      </div>
    );
  }

  const isTrade = decision.decision === "TRADE";

  return (
    <div
      className={cn(
        "rounded-lg border-l-4 border border-border bg-surface p-4",
        isTrade ? "border-l-violet-500" : "border-l-zinc-500",
      )}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4 text-violet-400" />
          <span className="text-xs font-semibold uppercase tracking-wide text-violet-400">
            Decision Agent · Qualitative (LLM)
          </span>
        </div>
        <StatusBadge
          label={decision.decision}
          tone={isTrade ? "info" : "neutral"}
        />
      </div>
      <p className="text-sm leading-relaxed text-foreground">
        {decision.reasoning}
      </p>
      {decision.confidence != null && (
        <div className="mt-2 text-xs text-muted-foreground">
          AI Confidence:{" "}
          <span className="font-mono text-foreground">
            {(decision.confidence * 100).toFixed(0)}%
          </span>
        </div>
      )}
    </div>
  );
}
