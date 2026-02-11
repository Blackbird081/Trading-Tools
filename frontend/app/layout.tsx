import type { Metadata } from "next";
import { Sidebar } from "@/components/sidebar";
import { TopNav } from "@/components/top-nav";
import { CommandPalette } from "@/components/command-palette";
import { WebSocketProvider } from "@/providers/ws-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Algo Trading Terminal",
  description: "Multi-Agent Algorithmic Trading System",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi" className="dark">
      <body className="bg-zinc-950 text-zinc-100 antialiased">
        <WebSocketProvider>
          <div className="flex h-screen overflow-hidden">
            <Sidebar />
            <div className="flex flex-1 flex-col">
              <TopNav />
              <main className="flex-1 overflow-hidden">{children}</main>
            </div>
          </div>
          <CommandPalette />
        </WebSocketProvider>
      </body>
    </html>
  );
}
