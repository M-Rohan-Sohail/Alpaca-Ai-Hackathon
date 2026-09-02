import { AlertTriangle, Inbox, RadioTower } from "lucide-react";
import { cn } from "@/lib/utils";

export function EmptyState({
  message = "No data available.",
  className,
}: {
  message?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border py-16 text-center",
        className,
      )}
    >
      <Inbox className="h-6 w-6 text-subtle-foreground" />
      <p className="text-sm text-muted-foreground">{message}</p>
    </div>
  );
}

export function ErrorState({
  message = "Something went wrong loading this data.",
  className,
}: {
  message?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-2 rounded-lg border border-loss/30 bg-loss-bg py-16 text-center",
        className,
      )}
    >
      <AlertTriangle className="h-6 w-6 text-loss" />
      <p className="text-sm text-loss">{message}</p>
    </div>
  );
}

export function LoadingSkeleton({
  rows = 4,
  className,
}: {
  rows?: number;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-3", className)}>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="h-14 w-full animate-pulse rounded-lg bg-surface border border-border"
        />
      ))}
    </div>
  );
}

export function StaleDataBanner({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-lg border border-warning/30 bg-warning-bg px-3 py-2 text-xs text-warning",
        className,
      )}
    >
      <RadioTower className="h-3.5 w-3.5 shrink-0" />
      <span className="font-medium">
        STALE DATA: Awaiting next pipeline update
      </span>
    </div>
  );
}
