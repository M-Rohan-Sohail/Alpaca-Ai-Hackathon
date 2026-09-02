import { Calculator, ShieldAlert } from "lucide-react";
import { cn, formatCurrency } from "@/lib/utils";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { PipelineCandidate } from "@/lib/api/types";

function formatCheckName(key: string): string {
  return key
    .split("_")
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(" ");
}

export function RiskAssessmentCard({
  evaluation,
}: {
  evaluation: PipelineCandidate["evaluations"][number] | undefined;
}) {
  if (!evaluation) {
    return (
      <div className="rounded-lg border border-dashed border-border p-4 text-sm text-subtle-foreground">
        Awaiting Risk Engine evaluation.
      </div>
    );
  }

  const isReject = evaluation.decision === "REJECT";
  const checks = Object.entries(evaluation.checks ?? {});

  return (
    <div className="flex flex-col gap-3">
      {isReject && (
        <div className="flex items-center gap-2 rounded-lg border-2 border-loss bg-loss-bg px-4 py-3">
          <ShieldAlert className="h-5 w-5 shrink-0 text-loss" />
          <span className="font-mono text-sm font-bold uppercase tracking-wide text-loss">
            Rejected by Risk Engine
          </span>
        </div>
      )}

      <div
        className={cn(
          "rounded-lg border-l-4 border border-border bg-surface p-4",
          isReject ? "border-l-loss" : "border-l-sky-500",
        )}
      >
        <div className="mb-3 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Calculator className="h-4 w-4 text-sky-400" />
            <span className="text-xs font-semibold uppercase tracking-wide text-sky-400">
              Risk Engine · Deterministic (Authority)
            </span>
          </div>
          <StatusBadge
            label={evaluation.decision}
            tone={isReject ? "loss" : "profit"}
          />
        </div>

        {checks.length > 0 && (
          <div className="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
            {checks.map(([name, result]) => (
              <div
                key={name}
                className={cn(
                  "flex items-center justify-between rounded-md border px-2 py-1.5 text-xs",
                  result === "PASS"
                    ? "border-profit/20 bg-profit-bg"
                    : "border-loss/30 bg-loss-bg",
                )}
              >
                <span className="text-muted-foreground truncate pr-1">
                  {formatCheckName(name)}
                </span>
                <span
                  className={cn(
                    "font-mono font-semibold",
                    result === "PASS" ? "text-profit" : "text-loss",
                  )}
                >
                  {result}
                </span>
              </div>
            ))}
          </div>
        )}

        <div className="grid grid-cols-2 gap-3 border-t border-border pt-3 text-xs">
          <div>
            <div className="text-muted-foreground">Approved Contracts</div>
            <div className="font-mono text-sm font-semibold text-foreground">
              {evaluation.order?.contracts ?? "N/A"}
            </div>
          </div>
          <div>
            <div className="text-muted-foreground">Capital at Risk</div>
            <div className="font-mono text-sm font-semibold text-foreground">
              {formatCurrency(evaluation.order?.capital_at_risk)}
            </div>
          </div>
          <div className="col-span-2">
            <div className="text-muted-foreground">Binding Constraint</div>
            <div className="font-mono text-sm font-semibold text-warning">
              {evaluation.binding_constraint
                ? formatCheckName(evaluation.binding_constraint)
                : "N/A"}
            </div>
          </div>
        </div>

        {evaluation.rejection_reasons.length > 0 && (
          <ul className="mt-3 flex flex-col gap-1 border-t border-border pt-3">
            {evaluation.rejection_reasons.map((reason, i) => (
              <li
                key={i}
                className="text-xs leading-relaxed text-loss"
              >
                • {reason}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
