import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

export function KpiCard({
  label,
  value,
  subValue,
  icon: Icon,
  progress,
  progressTone = "info",
  className,
}: {
  label: string;
  value: string;
  subValue?: string;
  icon?: LucideIcon;
  progress?: number | null;
  progressTone?: "info" | "warning" | "loss" | "profit";
  className?: string;
}) {
  const progressColor = {
    info: "bg-info",
    warning: "bg-warning",
    loss: "bg-loss",
    profit: "bg-profit",
  }[progressTone];

  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-surface p-4 flex flex-col gap-2",
        className,
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {label}
        </span>
        {Icon && <Icon className="h-4 w-4 text-subtle-foreground" />}
      </div>
      <div className="font-mono text-2xl font-semibold tabular-nums text-foreground">
        {value}
      </div>
      {subValue && (
        <div className="font-mono text-xs text-muted-foreground">{subValue}</div>
      )}
      {progress != null && (
        <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-border">
          <div
            className={cn("h-full rounded-full transition-all", progressColor)}
            style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
          />
        </div>
      )}
    </div>
  );
}
