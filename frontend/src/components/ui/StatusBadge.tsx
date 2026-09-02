import { cn } from "@/lib/utils";

export type BadgeTone = "profit" | "loss" | "warning" | "info" | "neutral";

const toneClasses: Record<BadgeTone, string> = {
  profit: "text-profit bg-profit-bg border-profit/30",
  loss: "text-loss bg-loss-bg border-loss/30",
  warning: "text-warning bg-warning-bg border-warning/30",
  info: "text-info bg-info-bg border-info/30",
  neutral: "text-neutral bg-neutral-bg border-neutral/30",
};

export function StatusBadge({
  label,
  tone,
  className,
}: {
  label: string;
  tone: BadgeTone;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium font-mono uppercase tracking-wide whitespace-nowrap",
        toneClasses[tone],
        className,
      )}
    >
      {label}
    </span>
  );
}
