"use client";

import { useEffect, useCallback, useState } from "react";
import { Command } from "cmdk";
import { useUIStore } from "@/stores/ui-store";
import {
  Briefcase,
  FileText,
  LayoutDashboard,
  Search,
  Settings,
  TrendingUp,
} from "lucide-react";
import { useRouter } from "next/navigation";

interface ParsedCommand {
  action: "BUY" | "SELL" | "NAVIGATE" | "UNKNOWN";
  symbol?: string;
  quantity?: number;
  price?: number;
  route?: string;
}

function parseCommand(input: string): ParsedCommand {
  const trimmed = input.trim().toUpperCase();

  // Try: "BUY FPT 1000 PRICE 98.5" or "BUY FPT 1000"
  const tradeMatch = trimmed.match(
    /^(BUY|SELL)\s+([A-Z]{3})\s+(\d+)(?:\s+(?:PRICE|@)\s+([\d.]+))?$/
  );
  if (tradeMatch) {
    return {
      action: tradeMatch[1] as "BUY" | "SELL",
      symbol: tradeMatch[2],
      quantity: parseInt(tradeMatch[3] ?? "0", 10),
      price: tradeMatch[4] ? parseFloat(tradeMatch[4]) : undefined,
    };
  }

  return { action: "UNKNOWN" };
}

export function CommandPalette() {
  const open = useUIStore((s) => s.commandPaletteOpen);
  const toggle = useUIStore((s) => s.toggleCommandPalette);
  const setActiveSymbol = useUIStore((s) => s.setActiveSymbol);
  const router = useRouter();
  const [search, setSearch] = useState("");

  // Ctrl+K global shortcut
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        toggle();
      }
      if (e.key === "Escape" && open) {
        toggle();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, toggle]);

  const handleSelect = useCallback(
    (value: string) => {
      // Navigation commands
      if (value.startsWith("/")) {
        router.push(value);
        toggle();
        return;
      }

      // Symbol selection
      if (/^[A-Z]{3}$/.test(value)) {
        setActiveSymbol(value);
        toggle();
        return;
      }

      // Trade command
      const parsed = parseCommand(value);
      if (parsed.action === "BUY" || parsed.action === "SELL") {
        // Would dispatch to order store in Phase 5
        toggle();
      }
    },
    [router, toggle, setActiveSymbol]
  );

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]">
      <div
        className="fixed inset-0 bg-black/60"
        onClick={toggle}
      />
      <Command
        className="relative w-[520px] rounded-xl border border-zinc-800 bg-zinc-900 shadow-2xl"
        shouldFilter={true}
      >
        <div className="flex items-center gap-2 border-b border-zinc-800 px-4">
          <Search className="h-4 w-4 text-zinc-500" />
          <Command.Input
            value={search}
            onValueChange={setSearch}
            placeholder="Type a command or search..."
            className="h-12 w-full bg-transparent text-sm text-zinc-100 placeholder:text-zinc-600 outline-none"
          />
        </div>

        <Command.List className="max-h-80 overflow-y-auto p-2">
          <Command.Empty className="py-4 text-center text-sm text-zinc-500">
            No results found.
          </Command.Empty>

          <Command.Group heading="Navigation" className="text-xs text-zinc-500 px-2 py-1.5">
            <Command.Item
              value="/"
              onSelect={handleSelect}
              className="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-zinc-300 cursor-pointer aria-selected:bg-zinc-800"
            >
              <LayoutDashboard className="h-4 w-4 text-zinc-500" />
              Dashboard
            </Command.Item>
            <Command.Item
              value="/portfolio"
              onSelect={handleSelect}
              className="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-zinc-300 cursor-pointer aria-selected:bg-zinc-800"
            >
              <Briefcase className="h-4 w-4 text-zinc-500" />
              Portfolio
            </Command.Item>
            <Command.Item
              value="/screener"
              onSelect={handleSelect}
              className="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-zinc-300 cursor-pointer aria-selected:bg-zinc-800"
            >
              <TrendingUp className="h-4 w-4 text-zinc-500" />
              Screener
            </Command.Item>
            <Command.Item
              value="/orders"
              onSelect={handleSelect}
              className="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-zinc-300 cursor-pointer aria-selected:bg-zinc-800"
            >
              <FileText className="h-4 w-4 text-zinc-500" />
              Order
            </Command.Item>
            <Command.Item
              value="/settings"
              onSelect={handleSelect}
              className="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-zinc-300 cursor-pointer aria-selected:bg-zinc-800"
            >
              <Settings className="h-4 w-4 text-zinc-500" />
              Settings
            </Command.Item>
          </Command.Group>

          <Command.Group heading="Quick Symbols" className="text-xs text-zinc-500 px-2 py-1.5">
            {["FPT", "VNM", "MWG", "HPG", "VCB"].map((sym) => (
              <Command.Item
                key={sym}
                value={sym}
                onSelect={handleSelect}
                className="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-zinc-300 cursor-pointer aria-selected:bg-zinc-800"
              >
                <span className="font-mono text-emerald-400">{sym}</span>
                <span className="text-zinc-500">View chart</span>
              </Command.Item>
            ))}
          </Command.Group>
        </Command.List>

        <div className="border-t border-zinc-800 px-4 py-2 text-xs text-zinc-600">
          Try: &quot;BUY FPT 1000 PRICE 98.5&quot; or navigate with arrow keys
        </div>
      </Command>
    </div>
  );
}

export { parseCommand };
