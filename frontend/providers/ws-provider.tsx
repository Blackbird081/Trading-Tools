"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { useMarketStore } from "@/stores/market-store";
import { useSignalStore } from "@/stores/signal-store";
import { usePortfolioStore } from "@/stores/portfolio-store";
import type { TickData, CandleData, AgentSignal, Position } from "@/types/market";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/market";

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    function connect() {
      try {
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onmessage = (event: MessageEvent) => {
          try {
            const msg = JSON.parse(event.data as string) as {
              type: string;
              payload: unknown;
            };
            routeMessage(msg);
          } catch {
            // Ignore malformed messages
          }
        };

        ws.onclose = () => {
          reconnectTimer.current = setTimeout(connect, 2000);
        };

        ws.onerror = () => ws.close();
      } catch {
        reconnectTimer.current = setTimeout(connect, 5000);
      }
    }

    connect();

    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, []);

  return <>{children}</>;
}

function routeMessage(msg: { type: string; payload: unknown }) {
  const { type, payload } = msg;
  switch (type) {
    case "tick":
      useMarketStore.getState().updateTick(payload as TickData);
      break;
    case "tick_batch":
      useMarketStore.getState().bulkUpdateTicks(payload as TickData[]);
      break;
    case "candle": {
      const cp = payload as { symbol: string; candle: CandleData };
      useMarketStore.getState().updateCandle(cp.symbol, cp.candle);
      break;
    }
    case "signal":
      useSignalStore.getState().addSignal(payload as AgentSignal);
      break;
    case "portfolio":
      usePortfolioStore.getState().sync(payload as {
        positions: Position[];
        cash: number;
        nav: number;
        purchasingPower: number;
      });
      break;
  }
}
