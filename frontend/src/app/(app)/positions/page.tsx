"use client";

import { useState } from "react";
import { usePositions, useCloseTrade } from "@/lib/api/hooks";
import { PositionTable } from "@/components/positions/PositionTable";
import { ConfirmationModal } from "@/components/ui/ConfirmationModal";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui/States";
import type { Position } from "@/lib/api/types";

export default function PositionsPage() {
  const { data: positions, isLoading, isError } = usePositions();
  const closeTrade = useCloseTrade();
  const [pendingClose, setPendingClose] = useState<Position | null>(null);

  async function handleConfirmClose() {
    if (!pendingClose) return;
    await closeTrade.mutateAsync({ strategy_id: pendingClose.strategy_id });
    setPendingClose(null);
  }

  if (isLoading) return <LoadingSkeleton rows={5} />;
  if (isError) return <ErrorState message="Failed to load open positions." />;
  if (!positions || positions.length === 0) {
    return <EmptyState message="No active positions." />;
  }

  return (
    <div className="flex flex-col gap-4">
      <PositionTable positions={positions} onRequestClose={setPendingClose} />

      <ConfirmationModal
        open={pendingClose != null}
        title="Force Close Position"
        description={
          pendingClose
            ? `You are about to manually close ${pendingClose.quantity} contract(s) of ${pendingClose.symbol} ${pendingClose.strategy_type}.`
            : ""
        }
        warning="This bypasses the deterministic holding rules managed by the Position Monitor. The order routes directly to the Execution Agent."
        confirmLabel="Force Close"
        isConfirming={closeTrade.isPending}
        onConfirm={handleConfirmClose}
        onCancel={() => setPendingClose(null)}
      />
    </div>
  );
}
