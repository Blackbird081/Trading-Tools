"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

type TradingMode = "dry-run" | "live";
type AiProvider = "deterministic" | "openvino" | "openai" | "anthropic" | "gemini" | "alibaba";

interface RuntimeSafetyBadgesProps {
  className?: string;
  requestedMode?: TradingMode;
}

function providerLabel(provider: AiProvider): string {
  if (provider === "openvino") return "OpenVINO";
  if (provider === "openai") return "OpenAI";
  if (provider === "anthropic") return "Anthropic";
  if (provider === "gemini") return "Gemini";
  if (provider === "alibaba") return "Alibaba";
  return "Deterministic";
}

export function RuntimeSafetyBadges({ className, requestedMode }: RuntimeSafetyBadgesProps) {
  const [runtimeMode, setRuntimeMode] = useState<TradingMode>("dry-run");
  const [aiProvider, setAiProvider] = useState<AiProvider>("deterministic");
  const [killSwitchActive, setKillSwitchActive] = useState(false);
  const [killSwitchReason, setKillSwitchReason] = useState("");
  const [marketSessionOpen, setMarketSessionOpen] = useState<boolean | null>(null);
  const [recentRejections10m, setRecentRejections10m] = useState<number>(0);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string>("");
  const [fetchError, setFetchError] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const refreshStatus = useCallback(async () => {
    setRefreshing(true);
    setFetchError("");
    try {
      const [setupRes, safetyRes] = await Promise.all([
        fetch(`${API_BASE}/setup/status`),
        fetch(`${API_BASE}/safety/status`),
      ]);

      if (!setupRes.ok || !safetyRes.ok) {
        throw new Error("Runtime safety status unavailable.");
      }

      const setupData = (await setupRes.json()) as { mode?: TradingMode; ai_provider?: AiProvider };
      const safetyData = (await safetyRes.json()) as {
        kill_switch?: { active?: boolean; reason?: string };
        market_session_open?: boolean;
        recent_rejections_10m?: number;
      };

      setRuntimeMode(setupData.mode === "live" ? "live" : "dry-run");
      setAiProvider(setupData.ai_provider ?? "deterministic");
      setKillSwitchActive(Boolean(safetyData.kill_switch?.active));
      setKillSwitchReason(String(safetyData.kill_switch?.reason ?? ""));
      setMarketSessionOpen(
        typeof safetyData.market_session_open === "boolean" ? safetyData.market_session_open : null,
      );
      setRecentRejections10m(
        typeof safetyData.recent_rejections_10m === "number" ? safetyData.recent_rejections_10m : 0,
      );
      setLastRefreshedAt(new Date().toLocaleTimeString("vi-VN"));
    } catch {
      setFetchError("Khong tai duoc trang thai an toan runtime.");
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void refreshStatus();
    const timer = window.setInterval(() => {
      void refreshStatus();
    }, 30000);
    return () => window.clearInterval(timer);
  }, [refreshStatus]);

  const modeMismatch = useMemo(
    () => Boolean(requestedMode && requestedMode !== runtimeMode),
    [requestedMode, runtimeMode],
  );

  return (
    <div className={`rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs ${className ?? ""}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`rounded-full px-2 py-1 font-semibold ${
            runtimeMode === "live"
              ? "bg-red-900/40 text-red-300 border border-red-800/70"
              : "bg-emerald-900/40 text-emerald-300 border border-emerald-800/70"
          }`}
        >
          Runtime: {runtimeMode}
        </span>
        <span
          className={`rounded-full px-2 py-1 font-semibold ${
            killSwitchActive
              ? "bg-red-900/40 text-red-300 border border-red-800/70"
              : "bg-emerald-900/40 text-emerald-300 border border-emerald-800/70"
          }`}
        >
          Kill-switch: {killSwitchActive ? "ON" : "OFF"}
        </span>
        <span className="rounded-full border border-blue-800/70 bg-blue-900/20 px-2 py-1 font-semibold text-blue-300">
          AI: {providerLabel(aiProvider)}
        </span>
        {typeof marketSessionOpen === "boolean" && (
          <span className="rounded-full border border-zinc-700 bg-zinc-950 px-2 py-1 text-zinc-300">
            Session: {marketSessionOpen ? "open" : "closed"}
          </span>
        )}
        <span className="rounded-full border border-zinc-700 bg-zinc-950 px-2 py-1 text-zinc-300">
          Rejections(10m): {recentRejections10m}
        </span>
        <button
          type="button"
          onClick={() => void refreshStatus()}
          className="rounded border border-zinc-700 px-2 py-1 text-zinc-300 hover:bg-zinc-800"
        >
          {refreshing ? "Refreshing..." : "Refresh safety"}
        </button>
      </div>

      {modeMismatch && (
        <p className="mt-2 rounded border border-amber-800/70 bg-amber-900/20 px-2 py-1 text-amber-200">
          Ban dang chon chay `{requestedMode}`, nhung runtime hien tai la `{runtimeMode}`.
        </p>
      )}
      {killSwitchActive && killSwitchReason && (
        <p className="mt-2 rounded border border-red-800/70 bg-red-900/20 px-2 py-1 text-red-200">
          Ly do kill-switch: {killSwitchReason}
        </p>
      )}
      {fetchError && (
        <p className="mt-2 rounded border border-amber-800/70 bg-amber-900/20 px-2 py-1 text-amber-200">
          {fetchError}
        </p>
      )}
      {lastRefreshedAt && <p className="mt-2 text-[11px] text-zinc-500">Last refresh: {lastRefreshedAt}</p>}
    </div>
  );
}
