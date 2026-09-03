"use client";

import { usePositions } from "@/lib/api/hooks";
import { PositionTable } from "@/components/positions/PositionTable";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui/States";

export default function PositionsPage() {
  const { data: positions, isLoading, isError } = usePositions();

  if (isLoading) return <LoadingSkeleton rows={5} />;
  if (isError) return <ErrorState message="Failed to load open positions." />;
  if (!positions || positions.length === 0) {
    return <EmptyState message="No active positions." />;
  }

  return (
    <div className="flex flex-col gap-4">
      <PositionTable positions={positions} />
    </div>
  );
}
