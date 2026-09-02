"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  GitBranch,
  LayoutDashboard,
  Layers,
  ShieldCheck,
  BookOpen,
  Activity,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/pipeline", label: "Pipeline Explorer", icon: GitBranch },
  { href: "/positions", label: "Positions", icon: Layers },
  { href: "/journal", label: "Trade Journal", icon: BookOpen },
  { href: "/risk-dashboard", label: "Risk Dashboard", icon: ShieldCheck },
];

export function Sidebar({ className }: { className?: string }) {
  const pathname = usePathname();

  return (
    <nav
      className={cn(
        "flex h-full w-56 shrink-0 flex-col border-r border-border bg-surface",
        className,
      )}
    >
      <div className="flex items-center gap-2 border-b border-border px-4 py-4">
        <Activity className="h-5 w-5 text-info" />
        <span className="font-mono text-sm font-semibold tracking-wide text-foreground">
          ALPACA TERMINAL
        </span>
      </div>
      <div className="flex flex-col gap-0.5 p-2">
        {NAV_ITEMS.map((item) => {
          const active =
            pathname === item.href || pathname?.startsWith(`${item.href}/`);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-info-bg text-info font-medium"
                  : "text-muted-foreground hover:bg-surface-hover hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="truncate">{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
