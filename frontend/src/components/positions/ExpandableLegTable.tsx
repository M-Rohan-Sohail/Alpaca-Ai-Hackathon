import { cn } from "@/lib/utils";
import { StrategyPayoffChart } from "@/components/charts/StrategyPayoffChart";
import type { PositionLeg } from "@/lib/api/types";

export function ExpandableLegTable({
  legs,
  maxLoss,
  maxProfit,
  breakeven,
  strategyType,
}: {
  legs: PositionLeg[];
  maxLoss?: number | null;
  maxProfit?: number | null;
  breakeven?: number[];
  strategyType?: string;
}) {
  return (
    <div className="flex flex-col gap-3">
      <div className="overflow-x-auto rounded-md border border-border bg-background">
        <table className="w-full min-w-[480px] text-xs">
          <thead>
            <tr className="border-b border-border text-muted-foreground">
              <th className="px-3 py-1.5 text-left font-medium">Side</th>
              <th className="px-3 py-1.5 text-left font-medium">Type</th>
              <th className="px-3 py-1.5 text-left font-medium">Strike</th>
              <th className="px-3 py-1.5 text-left font-medium">Expiration</th>
              <th className="px-3 py-1.5 text-left font-medium">OCC Symbol</th>
            </tr>
          </thead>
          <tbody className="font-mono">
            {legs.map((leg, i) => (
              <tr key={i} className="border-b border-border last:border-0">
                <td
                  className={cn(
                    "px-3 py-1.5 font-semibold",
                    leg.side === "BUY" ? "text-profit" : "text-loss",
                  )}
                >
                  {leg.side}
                </td>
                <td className="px-3 py-1.5">{leg.option_type}</td>
                <td className="px-3 py-1.5">{leg.strike}</td>
                <td className="px-3 py-1.5">{leg.expiration}</td>
                <td className="px-3 py-1.5 text-subtle-foreground">
                  {leg.occ_symbol}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {maxLoss != null && maxProfit != null && breakeven && breakeven.length > 0 && (
        <StrategyPayoffChart
          legs={legs}
          maxLoss={maxLoss}
          maxProfit={maxProfit}
          breakeven={breakeven}
          strategyType={strategyType ?? ""}
        />
      )}
    </div>
  );
}
