"use client";

import { useEffect, useMemo, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
const STORAGE_KEY = "tt.local.setup.draft.v1";

type TradingMode = "dry-run" | "live";

interface SetupDraft {
  tradingMode: TradingMode;
  duckdbPath: string;
  vnstockApiKey: string;
  ssiConsumerId: string;
  ssiConsumerSecret: string;
  ssiAccountNo: string;
  ssiPrivateKeyB64: string;
  aiModelPath: string;
}

interface CheckItem {
  name: string;
  status: "ok" | "warn";
  detail: string;
}

const DEFAULT_DRAFT: SetupDraft = {
  tradingMode: "dry-run",
  duckdbPath: "data/trading.duckdb",
  vnstockApiKey: "",
  ssiConsumerId: "",
  ssiConsumerSecret: "",
  ssiAccountNo: "",
  ssiPrivateKeyB64: "",
  aiModelPath: "data/models/phi-3-mini-int4",
};

function statusClass(status: "ok" | "warn"): string {
  return status === "ok"
    ? "border-emerald-800/60 bg-emerald-900/20 text-emerald-300"
    : "border-amber-800/60 bg-amber-900/20 text-amber-200";
}

export function SetupWizard() {
  const [draft, setDraft] = useState<SetupDraft>(DEFAULT_DRAFT);
  const [runtimeChecks, setRuntimeChecks] = useState<CheckItem[]>([]);
  const [validateChecks, setValidateChecks] = useState<CheckItem[]>([]);
  const [runtimeMode, setRuntimeMode] = useState<TradingMode>("dry-run");
  const [runtimeDataPath, setRuntimeDataPath] = useState<string>("-");
  const [busy, setBusy] = useState<"idle" | "runtime" | "validate" | "init">("idle");
  const [message, setMessage] = useState<string>("");

  useEffect(() => {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    try {
      const parsed = JSON.parse(raw) as Partial<SetupDraft>;
      setDraft((prev) => ({ ...prev, ...parsed }));
    } catch {
      // ignore corrupted local storage and keep defaults
    }
  }, []);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(draft));
  }, [draft]);

  const localReady = useMemo(
    () =>
      runtimeChecks.length > 0 &&
      runtimeChecks.every((item) => item.status === "ok"),
    [runtimeChecks],
  );

  const updateDraft = <K extends keyof SetupDraft>(key: K, value: SetupDraft[K]) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
  };

  const fetchRuntimeStatus = async () => {
    setBusy("runtime");
    setMessage("");
    try {
      const res = await fetch(`${API_BASE}/setup/status`);
      const data = (await res.json()) as {
        mode?: TradingMode;
        data_path?: string;
        checks?: CheckItem[];
      };
      setRuntimeMode(data.mode ?? "dry-run");
      setRuntimeDataPath(data.data_path ?? "-");
      setRuntimeChecks(Array.isArray(data.checks) ? data.checks : []);
      setMessage("Runtime status refreshed.");
    } catch {
      setMessage("Cannot reach backend setup status API.");
    } finally {
      setBusy("idle");
    }
  };

  const validateDraft = async () => {
    setBusy("validate");
    setMessage("");
    try {
      const res = await fetch(`${API_BASE}/setup/validate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          trading_mode: draft.tradingMode,
          duckdb_path: draft.duckdbPath,
          vnstock_api_key: draft.vnstockApiKey,
          ssi_consumer_id: draft.ssiConsumerId,
          ssi_consumer_secret: draft.ssiConsumerSecret,
          ssi_account_no: draft.ssiAccountNo,
          ssi_private_key_b64: draft.ssiPrivateKeyB64,
          ai_model_path: draft.aiModelPath,
        }),
      });
      const data = (await res.json()) as { checks?: CheckItem[]; valid?: boolean };
      setValidateChecks(Array.isArray(data.checks) ? data.checks : []);
      setMessage(data.valid ? "Validation passed." : "Validation finished with warnings.");
    } catch {
      setMessage("Validation request failed.");
    } finally {
      setBusy("idle");
    }
  };

  const initLocalPath = async () => {
    setBusy("init");
    setMessage("");
    try {
      const res = await fetch(`${API_BASE}/setup/init-local`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ duckdb_path: draft.duckdbPath }),
      });
      if (!res.ok) {
        setMessage("Failed to initialize local path.");
        return;
      }
      await fetchRuntimeStatus();
      setMessage("Local data path initialized.");
    } catch {
      setMessage("Initialization failed.");
    } finally {
      setBusy("idle");
    }
  };

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h2 className="mb-3 text-sm font-medium text-zinc-300">Step 1 — Local Profile</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="space-y-1">
            <span className="text-xs text-zinc-500">Trading mode</span>
            <select
              value={draft.tradingMode}
              onChange={(e) => updateDraft("tradingMode", e.target.value as TradingMode)}
              className="w-full rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100"
            >
              <option value="dry-run">dry-run (recommended)</option>
              <option value="live">live</option>
            </select>
          </label>
          <label className="space-y-1">
            <span className="text-xs text-zinc-500">DuckDB path</span>
            <input
              value={draft.duckdbPath}
              onChange={(e) => updateDraft("duckdbPath", e.target.value)}
              className="w-full rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100"
            />
          </label>
        </div>
      </div>

      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h2 className="mb-3 text-sm font-medium text-zinc-300">Step 2 — Key Input (local draft)</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <input
            value={draft.vnstockApiKey}
            onChange={(e) => updateDraft("vnstockApiKey", e.target.value)}
            placeholder="VNSTOCK_API_KEY"
            className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500"
          />
          <input
            value={draft.ssiConsumerId}
            onChange={(e) => updateDraft("ssiConsumerId", e.target.value)}
            placeholder="SSI_CONSUMER_ID"
            className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500"
          />
          <input
            value={draft.ssiConsumerSecret}
            onChange={(e) => updateDraft("ssiConsumerSecret", e.target.value)}
            placeholder="SSI_CONSUMER_SECRET"
            className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500"
          />
          <input
            value={draft.ssiAccountNo}
            onChange={(e) => updateDraft("ssiAccountNo", e.target.value)}
            placeholder="SSI_ACCOUNT_NO"
            className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500"
          />
          <textarea
            value={draft.ssiPrivateKeyB64}
            onChange={(e) => updateDraft("ssiPrivateKeyB64", e.target.value)}
            placeholder="SSI_PRIVATE_KEY_B64"
            className="min-h-20 rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 sm:col-span-2"
          />
          <input
            value={draft.aiModelPath}
            onChange={(e) => updateDraft("aiModelPath", e.target.value)}
            placeholder="OPENVINO_MODEL_PATH"
            className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 sm:col-span-2"
          />
        </div>
      </div>

      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h2 className="mb-3 text-sm font-medium text-zinc-300">Step 3 — Validate and Initialize</h2>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={validateDraft}
            disabled={busy !== "idle"}
            className="rounded bg-blue-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
          >
            {busy === "validate" ? "Validating..." : "Validate"}
          </button>
          <button
            onClick={fetchRuntimeStatus}
            disabled={busy !== "idle"}
            className="rounded bg-zinc-700 px-3 py-2 text-xs font-semibold text-zinc-100 disabled:opacity-50"
          >
            {busy === "runtime" ? "Refreshing..." : "Refresh Runtime Status"}
          </button>
          <button
            onClick={initLocalPath}
            disabled={busy !== "idle"}
            className="rounded bg-emerald-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
          >
            {busy === "init" ? "Initializing..." : "Initialize Local Data Path"}
          </button>
        </div>

        {message && <p className="mt-3 text-xs text-zinc-400">{message}</p>}

        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <div className="space-y-2">
            <div className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Validation checks</div>
            <div className="space-y-2">
              {validateChecks.length === 0 && (
                <div className="rounded border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-zinc-500">
                  Run Validate to see results.
                </div>
              )}
              {validateChecks.map((item) => (
                <div key={`val-${item.name}`} className={`rounded border px-3 py-2 text-xs ${statusClass(item.status)}`}>
                  <div className="font-semibold">{item.name}</div>
                  <div className="opacity-90">{item.detail}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Runtime status</div>
            <div className="rounded border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-zinc-300">
              <div>Mode: {runtimeMode}</div>
              <div>Data path: {runtimeDataPath}</div>
              <div>Ready: {localReady ? "yes" : "no"}</div>
            </div>
            <div className="space-y-2">
              {runtimeChecks.map((item) => (
                <div key={`run-${item.name}`} className={`rounded border px-3 py-2 text-xs ${statusClass(item.status)}`}>
                  <div className="font-semibold">{item.name}</div>
                  <div className="opacity-90">{item.detail}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

