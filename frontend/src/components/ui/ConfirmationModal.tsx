"use client";

import { AlertTriangle, X } from "lucide-react";
import { useEffect } from "react";
import { cn } from "@/lib/utils";

export function ConfirmationModal({
  open,
  title,
  description,
  warning,
  confirmLabel = "Confirm",
  isConfirming = false,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  description: string;
  warning?: string;
  confirmLabel?: string;
  isConfirming?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="w-full max-w-md rounded-lg border border-border-strong bg-surface shadow-2xl">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <h2 className="text-sm font-semibold text-foreground">{title}</h2>
          <button
            onClick={onCancel}
            className="rounded p-1 text-subtle-foreground hover:bg-surface-hover hover:text-foreground"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="flex flex-col gap-3 px-4 py-4">
          <p className="text-sm text-muted-foreground">{description}</p>
          {warning && (
            <div className="flex items-start gap-2 rounded-md border border-warning/30 bg-warning-bg px-3 py-2 text-xs text-warning">
              <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
              <span>{warning}</span>
            </div>
          )}
        </div>
        <div className="flex items-center justify-end gap-2 border-t border-border px-4 py-3">
          <button
            onClick={onCancel}
            disabled={isConfirming}
            className="rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground hover:bg-surface-hover disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isConfirming}
            className={cn(
              "rounded-md bg-loss px-3 py-1.5 text-sm font-medium text-white hover:bg-loss/90 disabled:opacity-50",
            )}
          >
            {isConfirming ? "Submitting..." : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
