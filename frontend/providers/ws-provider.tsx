"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { useMarketStore } from "@/stores/market-store";
import { useSignalStore } from "@/stores/signal-store";
import { usePortfolioStore } from "@/stores/portfolio-store";
import type { TickData, CandleData, AgentSignal, Position } from "@/types/market";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/market";

// ★ Exponential backoff constants
const RECONNECT_BASE_MS = 1_000;   // 1s initial delay
const RECONNECT_MAX_MS = 30_000;   // 30s max delay
const RECONNECT_JITTER_MS = 500;   // ±500ms jitter to avoid thundering herd

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const attemptRef = useRef<number>(0);  // ★ Track reconnect attempts for backoff

  useEffect(() => {
    function connect() {
      try {
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          clearTimeout(reconnectTimer.current);
          attemptRef.current = 0;  // ★ Reset backoff on successful connection
          console.debug("[WS] Connected to", WS_URL);
        };

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
          // ★ Exponential backoff: delay = min(base * 2^attempt + jitter, max)
          const attempt = attemptRef.current;
          const backoff = Math.min(
            RECONNECT_BASE_MS * Math.pow(2, attempt) + Math.random() * RECONNECT_JITTER_MS,
            RECONNECT_MAX_MS,
          );
          attemptRef.current = attempt + 1;
          console.debug(`[WS] Disconnected. Reconnecting in ${Math.round(backoff)}ms (attempt ${attempt + 1})`);
          reconnectTimer.current = setTimeout(connect, backoff);
        };

        ws.onerror = () => ws.close();
      } catch {
        // ★ Also use backoff for initial connection failures
        const attempt = attemptRef.current;
        const backoff = Math.min(
          RECONNECT_BASE_MS * Math.pow(2, attempt) + Math.random() * RECONNECT_JITTER_MS,
          RECONNECT_MAX_MS,
        );
        attemptRef.current = attempt + 1;
        reconnectTimer.current = setTimeout(connect, backoff);
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
