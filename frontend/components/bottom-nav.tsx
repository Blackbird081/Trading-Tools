"use client";

/**
 * Bottom Navigation — Mobile-only navigation bar.
 * ★ Fixed at bottom of screen on mobile devices.
 * ★ Shows 5 main navigation items with icons.
 */

import {
  BarChart3,
  Briefcase,
  FileText,
  LayoutDashboard,
  TrendingUp,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/market-board", label: "Bảng điện", icon: BarChart3 },
  { href: "/portfolio", label: "Portfolio", icon: Briefcase },
  { href: "/screener", label: "Screener", icon: TrendingUp },
  { href: "/orders", label: "Lệnh", icon: FileText },
];

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 flex h-16 items-center justify-around border-t border-zinc-800 bg-zinc-950/95 backdrop-blur-sm">
      {navItems.map((item) => {
        const isActive = pathname === item.href;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex flex-col items-center gap-0.5 px-3 py-2 rounded-lg transition-colors",
              isActive
                ? "text-emerald-400"
                : "text-zinc-500 hover:text-zinc-300",
            )}
          >
            <item.icon className={cn("h-5 w-5", isActive && "text-emerald-400")} />
            <span className="text-[10px] font-medium">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
