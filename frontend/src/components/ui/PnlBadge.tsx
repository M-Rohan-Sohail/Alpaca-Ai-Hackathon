import { cn } from "@/lib/utils";
import { formatCurrency, formatPercent } from "@/lib/utils";

export function PnlBadge({
  value,
  variant = "currency",
  className,
}: {
  value: number | null | undefined;
  variant?: "currency" | "percent";
  className?: string;
}) {
  if (value == null || Number.isNaN(value)) {
    return (
      <span className={cn("font-mono text-sm text-subtle-foreground", className)}>
        N/A
      </span>
    );
  }

  const positive = value > 0;
  const negative = value < 0;
  const text = variant === "currency" ? formatCurrency(value) : formatPercent(value);

  return (
    <span
      className={cn(
        "font-mono text-sm font-medium tabular-nums",
        positive && "text-profit",
        negative && "text-loss",
        !positive && !negative && "text-muted-foreground",
        className,
      )}
    >
      {variant === "currency" && positive ? `+${text}` : text}
    </span>
  );
}
