"use client";

import { useUIStore } from "@/stores/ui-store";
import {
  BarChart3,
  Briefcase,
  FileText,
  LayoutDashboard,
  Settings,
  TrendingUp,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/market-board", label: "Market Board", icon: BarChart3 },
  { href: "/portfolio", label: "Portfolio", icon: Briefcase },
  { href: "/screener", label: "Screener", icon: TrendingUp },
  { href: "/orders", label: "Order", icon: FileText },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const collapsed = useUIStore((s) => s.sidebarCollapsed);
  const pathname = usePathname();

  return (
    <aside
      className={cn(
        "flex flex-col border-r border-zinc-800 bg-zinc-950 transition-all duration-200",
        collapsed ? "w-16" : "w-56"
      )}
    >
      <div className="flex h-14 items-center gap-2 border-b border-zinc-800 px-4">
        <BarChart3 className="h-6 w-6 text-emerald-400" />
        {!collapsed && (
          <span className="text-sm font-semibold tracking-tight">
            AlgoTrader
          </span>
        )}
      </div>

      <nav className="flex-1 space-y-1 p-2">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-zinc-800 text-emerald-400"
                  : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200"
              )}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
