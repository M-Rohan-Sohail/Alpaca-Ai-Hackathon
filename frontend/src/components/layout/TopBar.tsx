"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState, useSyncExternalStore } from "react";

const PAGE_TITLES: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/pipeline": "Pipeline Explorer",
  "/positions": "Open Positions & Exit Monitor",
  "/journal": "Trade Journal",
  "/risk-dashboard": "Risk Dashboard",
};

function subscribeNoop() {
  return () => {};
}

// Mirrors the mount-detection pattern react-hooks/set-state-in-effect steers
// you toward: useSyncExternalStore returns different snapshots for the
// server render and the first client render without ever calling setState
// synchronously in an effect body.
function useIsClient() {
  return useSyncExternalStore(
    subscribeNoop,
    () => true,
    () => false,
  );
}

export function TopBar() {
  const pathname = usePathname();
  const isClient = useIsClient();
  const [now, setNow] = useState<Date>(() => new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const title =
    Object.entries(PAGE_TITLES).find(([path]) => pathname?.startsWith(path))
      ?.[1] ?? "Terminal";

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-surface px-6">
      <h1 className="text-sm font-semibold text-foreground">{title}</h1>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-profit opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-profit" />
          </span>
          <span>Live</span>
        </div>
        <span className="font-mono text-xs text-subtle-foreground tabular-nums">
          {isClient
            ? now.toLocaleTimeString("en-US", {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              })
            : "--:--:--"}
        </span>
      </div>
    </header>
  );
}
