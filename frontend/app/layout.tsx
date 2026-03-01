import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import { Sidebar } from "@/components/sidebar";
import { TopNav } from "@/components/top-nav";
import { BottomNav } from "@/components/bottom-nav";
import { CommandPalette } from "@/components/command-palette";
import { SymbolPopup } from "@/components/symbol-popup";
import { WebSocketProvider } from "@/providers/ws-provider";
import "./globals.css";

const inter = Inter({ subsets: ["latin", "vietnamese"] });

export const metadata: Metadata = {
  title: "Algo Trading Terminal",
  description: "Multi-Agent Algorithmic Trading System",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi" className="dark">
      <body className={`bg-zinc-950 text-zinc-100 antialiased text-[15px] ${inter.className}`}>
        <WebSocketProvider>
          {/* Desktop layout: sidebar + main */}
          <div className="hidden md:flex h-screen overflow-hidden">
            <Sidebar />
            <div className="flex flex-1 flex-col min-w-0">
              <TopNav />
              <main className="flex-1 overflow-auto min-h-0">{children}</main>
            </div>
          </div>

          {/* Mobile layout: top nav + main + bottom nav */}
          <div className="flex h-dvh min-h-dvh flex-col overflow-hidden md:hidden">
            <TopNav />
            <main className="min-h-0 flex-1 overflow-auto pb-[calc(64px+env(safe-area-inset-bottom,0px))]">
              {children}
            </main>
            <BottomNav />
          </div>

          <CommandPalette />
          {/* ★ Symbol popup — available globally, triggered by openSymbolPopup() */}
          <SymbolPopup />
        </WebSocketProvider>
      </body>
    </html>
  );
}
