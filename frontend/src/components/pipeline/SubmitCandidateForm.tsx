"use client";

import { useState } from "react";
import { Loader2, Send } from "lucide-react";
import { useSubmitCandidate } from "@/lib/api/hooks";
import { cn } from "@/lib/utils";

export function SubmitCandidateForm() {
  const [symbol, setSymbol] = useState("");
  const { mutate, data, isPending, isError, error, reset } = useSubmitCandidate();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = symbol.trim();
    if (!trimmed) return;
    mutate(trimmed, {
      onSuccess: () => setSymbol(""),
    });
  }

  return (
    <div className="rounded-lg border border-border bg-surface p-3">
      <form onSubmit={handleSubmit} className="flex items-center gap-2">
        <input
          value={symbol}
          onChange={(e) => {
            setSymbol(e.target.value);
            if (data || isError) reset();
          }}
          placeholder="Submit a ticker for processing (e.g. NVDA)"
          className="flex-1 rounded-md border border-border bg-background px-3 py-1.5 text-sm font-mono uppercase text-foreground placeholder:font-sans placeholder:normal-case placeholder:text-subtle-foreground focus:outline-none focus:ring-1 focus:ring-border-strong"
          maxLength={10}
        />
        <button
          type="submit"
          disabled={isPending || !symbol.trim()}
          className={cn(
            "flex items-center gap-1.5 rounded-md bg-foreground px-3 py-1.5 text-sm font-medium text-background hover:bg-foreground/90 disabled:opacity-50",
          )}
        >
          {isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Send className="h-3.5 w-3.5" />
          )}
          Submit
        </button>
      </form>
      {isError && (
        <p className="mt-2 text-xs text-loss">
          {error instanceof Error ? error.message : "Submission failed."}
        </p>
      )}
      {data && (
        <p className="mt-2 text-xs text-muted-foreground">{data.message}</p>
      )}
    </div>
  );
}
