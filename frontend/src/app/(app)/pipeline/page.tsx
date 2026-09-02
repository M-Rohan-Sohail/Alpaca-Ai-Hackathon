"use client";

import { useState } from "react";
import { usePipelineLatest } from "@/lib/api/hooks";
import { CandidateList } from "@/components/pipeline/CandidateList";
import { PipelineStepper } from "@/components/pipeline/PipelineStepper";
import { EmptyState, ErrorState, LoadingSkeleton, StaleDataBanner } from "@/components/ui/States";
import { isStale } from "@/lib/utils";

export default function PipelinePage() {
  const { data: candidates, isLoading, isError } = usePipelineLatest();
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);

  if (isLoading) {
    return <LoadingSkeleton rows={6} />;
  }

  if (isError) {
    return <ErrorState message="Failed to load pipeline candidates." />;
  }

  if (!candidates || candidates.length === 0) {
    return <EmptyState message="No candidates have been processed yet." />;
  }

  const selected =
    candidates.find((c) => c.symbol === selectedSymbol) ?? candidates[0];

  return (
    <div className="flex h-full flex-col gap-4">
      {isStale(selected.updated_at) && <StaleDataBanner />}
      <div className="flex flex-1 flex-col gap-4 lg:flex-row lg:overflow-hidden">
        <div className="shrink-0 lg:w-72 lg:overflow-y-auto">
          <div className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Candidates Processed Today ({candidates.length})
          </div>
          <CandidateList
            candidates={candidates}
            selectedSymbol={selected.symbol}
            onSelect={setSelectedSymbol}
          />
        </div>
        <div className="min-w-0 flex-1 lg:overflow-y-auto lg:pr-2">
          <div className="mb-3 flex items-center gap-2">
            <h2 className="font-mono text-lg font-semibold text-foreground">
              {selected.symbol}
            </h2>
          </div>
          <PipelineStepper candidate={selected} />
        </div>
      </div>
    </div>
  );
}
