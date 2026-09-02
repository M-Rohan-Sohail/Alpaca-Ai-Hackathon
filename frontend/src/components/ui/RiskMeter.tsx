import { cn, formatCurrency } from "@/lib/utils";

export function RiskMeter({
  label,
  used,
  limit,
  className,
}: {
  label: string;
  used: number | null | undefined;
  limit: number | null | undefined;
  className?: string;
}) {
  const hasData = used != null && limit != null && limit > 0;
  const pct = hasData ? Math.min(100, (used / limit) * 100) : 0;

  const tone = pct >= 90 ? "bg-loss" : pct >= 70 ? "bg-warning" : "bg-info";

  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-mono text-foreground tabular-nums">
          {hasData
            ? `${formatCurrency(used)} / ${formatCurrency(limit)}`
            : "N/A"}
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-border">
        <div
          className={cn("h-full rounded-full transition-all", tone)}
          style={{ width: `${hasData ? pct : 0}%` }}
        />
      </div>
    </div>
  );
}
