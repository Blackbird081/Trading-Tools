"use client";

import { useEffect, useMemo, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
const STORAGE_KEY = "tt.local.setup.draft.v1";

type TradingMode = "dry-run" | "live";
type AiProvider = "deterministic" | "openvino" | "openai" | "anthropic" | "gemini" | "alibaba";

interface SetupDraft {
  tradingMode: TradingMode;
  duckdbPath: string;
  vnstockApiKey: string;
  ssiConsumerId: string;
  ssiConsumerSecret: string;
  ssiAccountNo: string;
  ssiPrivateKeyB64: string;
  aiProvider: AiProvider;
  openaiApiKey: string;
  openaiModel: string;
  openaiModelCoder: string;
  openaiModelWriting: string;
  anthropicApiKey: string;
  anthropicModel: string;
  anthropicModelCoder: string;
  anthropicModelWriting: string;
  geminiApiKey: string;
  geminiModel: string;
  geminiModelCoder: string;
  geminiModelWriting: string;
  alibabaApiKey: string;
  alibabaBaseUrl: string;
  alibabaModelCoder: string;
  alibabaModelReasoning: string;
  alibabaModelWriting: string;
  aiFallbackOrder: string;
  aiTimeoutSeconds: number;
  aiBudgetUsdPerRun: number;
  aiMaxRemoteCalls: number;
  aiModelPath: string;
}

interface CheckItem {
  name: string;
  status: "ok" | "warn";
  detail: string;
}

interface ProfileInfo {
  name: string;
  file: string;
  revoked: boolean;
  created_at: string;
  updated_at: string;
}

const DEFAULT_DRAFT: SetupDraft = {
  tradingMode: "dry-run",
  duckdbPath: "data/trading.duckdb",
  vnstockApiKey: "",
  ssiConsumerId: "",
  ssiConsumerSecret: "",
  ssiAccountNo: "",
  ssiPrivateKeyB64: "",
  aiProvider: "deterministic",
  openaiApiKey: "",
  openaiModel: "gpt-4o-mini",
  openaiModelCoder: "gpt-4o-mini",
  openaiModelWriting: "gpt-4o-mini",
  anthropicApiKey: "",
  anthropicModel: "claude-3-5-haiku-latest",
  anthropicModelCoder: "claude-3-5-haiku-latest",
  anthropicModelWriting: "claude-3-5-haiku-latest",
  geminiApiKey: "",
  geminiModel: "gemini-1.5-flash",
  geminiModelCoder: "gemini-1.5-flash",
  geminiModelWriting: "gemini-1.5-flash",
  alibabaApiKey: "",
  alibabaBaseUrl: "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
  alibabaModelCoder: "qwen2.5-coder-32b-instruct",
  alibabaModelReasoning: "kimi-k2.5",
  alibabaModelWriting: "minimax-m2.5",
  aiFallbackOrder: "anthropic,gemini,alibaba,deterministic",
  aiTimeoutSeconds: 20,
  aiBudgetUsdPerRun: 0.25,
  aiMaxRemoteCalls: 40,
  aiModelPath: "data/models/phi-3-mini-int4",
};

interface ModelRecommendationRow {
  task: string;
  role: string;
  goal: string;
  openai: string;
  anthropic: string;
  gemini: string;
  alibaba: string;
}

function statusClass(status: "ok" | "warn"): string {
  return status === "ok"
    ? "border-emerald-800/60 bg-emerald-900/20 text-emerald-300"
    : "border-amber-800/60 bg-amber-900/20 text-amber-200";
}

export function SetupWizard() {
  const [draft, setDraft] = useState<SetupDraft>(DEFAULT_DRAFT);
  const [runtimeChecks, setRuntimeChecks] = useState<CheckItem[]>([]);
  const [validateChecks, setValidateChecks] = useState<CheckItem[]>([]);
  const [probeChecks, setProbeChecks] = useState<CheckItem[]>([]);
  const [runtimeMode, setRuntimeMode] = useState<TradingMode>("dry-run");
  const [runtimeDataPath, setRuntimeDataPath] = useState<string>("-");
  const [runtimeAiProvider, setRuntimeAiProvider] = useState<AiProvider>("deterministic");
  const [runtimeOpenAiModel, setRuntimeOpenAiModel] = useState<string>("gpt-4o-mini");
  const [runtimeAnthropicModel, setRuntimeAnthropicModel] = useState<string>("claude-3-5-haiku-latest");
  const [runtimeGeminiModel, setRuntimeGeminiModel] = useState<string>("gemini-1.5-flash");
  const [runtimeAlibabaModelReasoning, setRuntimeAlibabaModelReasoning] = useState<string>("kimi-k2.5");
  const [runtimeFallbackOrder, setRuntimeFallbackOrder] = useState<string>("anthropic,gemini,alibaba,deterministic");
  const [runtimeTimeoutSeconds, setRuntimeTimeoutSeconds] = useState<number>(20);
  const [runtimeBudgetUsd, setRuntimeBudgetUsd] = useState<number>(0.25);
  const [runtimeMaxRemoteCalls, setRuntimeMaxRemoteCalls] = useState<number>(40);
  const [modelRecommendations, setModelRecommendations] = useState<ModelRecommendationRow[]>([]);
  const [busy, setBusy] = useState<"idle" | "runtime" | "validate" | "init" | "probe">("idle");
  const [message, setMessage] = useState<string>("");
  const [profiles, setProfiles] = useState<ProfileInfo[]>([]);
  const [activeProfile, setActiveProfile] = useState<string | null>(null);
  const [profileName, setProfileName] = useState("default");
  const [profilePassphrase, setProfilePassphrase] = useState("");
  const [profileMsg, setProfileMsg] = useState("");
  const [importPayload, setImportPayload] = useState("");
  const [rotateOldPass, setRotateOldPass] = useState("");
  const [rotateNewPass, setRotateNewPass] = useState("");
  const [savedDraftJson, setSavedDraftJson] = useState<string>(JSON.stringify(DEFAULT_DRAFT));
  const [lastSavedAt, setLastSavedAt] = useState<string>("");

  useEffect(() => {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      const fallback = JSON.stringify(DEFAULT_DRAFT);
      setSavedDraftJson(fallback);
      return;
    }
    try {
      const parsed = JSON.parse(raw) as Partial<SetupDraft>;
      const merged = { ...DEFAULT_DRAFT, ...parsed };
      const serialized = JSON.stringify(merged);
      setDraft(merged);
      setSavedDraftJson(serialized);
    } catch {
      const fallback = JSON.stringify(DEFAULT_DRAFT);
      setSavedDraftJson(fallback);
      // ignore corrupted local storage and keep defaults
    }
  }, []);

  const fetchProfiles = async () => {
    try {
      const res = await fetch(`${API_BASE}/setup/profiles`);
      const data = (await res.json()) as { active_profile?: string | null; profiles?: ProfileInfo[] };
      setProfiles(Array.isArray(data.profiles) ? data.profiles : []);
      setActiveProfile(data.active_profile ?? null);
    } catch {
      setProfileMsg("Cannot fetch profiles.");
    }
  };

  useEffect(() => {
    void fetchProfiles();
  }, []);

  useEffect(() => {
    const fetchModelRecommendations = async () => {
      try {
        const res = await fetch(`${API_BASE}/setup/model-recommendations`);
        const data = (await res.json()) as { matrix?: ModelRecommendationRow[] };
        setModelRecommendations(Array.isArray(data.matrix) ? data.matrix : []);
      } catch {
        setModelRecommendations([]);
      }
    };
    void fetchModelRecommendations();
  }, []);

  const localReady = useMemo(
    () =>
      runtimeChecks.length > 0 &&
      runtimeChecks.every((item) => item.status === "ok"),
    [runtimeChecks],
  );

  const updateDraft = <K extends keyof SetupDraft>(key: K, value: SetupDraft[K]) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
  };
  const draftJson = useMemo(() => JSON.stringify(draft), [draft]);
  const isDraftDirty = draftJson !== savedDraftJson;

  const saveDraftLocal = () => {
    try {
      localStorage.setItem(STORAGE_KEY, draftJson);
      setSavedDraftJson(draftJson);
      setLastSavedAt(new Date().toLocaleString());
      setMessage("Draft saved locally.");
    } catch {
      setMessage("Cannot save draft to local storage.");
    }
  };

  const resetToSavedDraft = () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        const fallback = JSON.stringify(DEFAULT_DRAFT);
        setDraft(DEFAULT_DRAFT);
        setSavedDraftJson(fallback);
        setMessage("No saved draft found. Reset to defaults.");
        return;
      }
      const parsed = JSON.parse(raw) as Partial<SetupDraft>;
      const merged = { ...DEFAULT_DRAFT, ...parsed };
      const serialized = JSON.stringify(merged);
      setDraft(merged);
      setSavedDraftJson(serialized);
      setMessage("Reverted to saved draft.");
    } catch {
      setMessage("Cannot restore saved draft.");
    }
  };

  const runtimeAiModel =
    runtimeAiProvider === "openai"
      ? runtimeOpenAiModel
      : runtimeAiProvider === "anthropic"
        ? runtimeAnthropicModel
        : runtimeAiProvider === "gemini"
          ? runtimeGeminiModel
          : runtimeAiProvider === "alibaba"
            ? runtimeAlibabaModelReasoning
          : runtimeAiProvider === "openvino"
            ? draft.aiModelPath
            : "deterministic-v1";

  const fetchRuntimeStatus = async () => {
    setBusy("runtime");
    setMessage("");
    try {
      const res = await fetch(`${API_BASE}/setup/status`);
      const data = (await res.json()) as {
        mode?: TradingMode;
        data_path?: string;
        ai_provider?: AiProvider;
        openai_model?: string;
        anthropic_model?: string;
        gemini_model?: string;
        alibaba_model_reasoning?: string;
        ai_fallback_order?: string;
        ai_timeout_seconds?: number;
        ai_budget_usd_per_run?: number;
        ai_max_remote_calls?: number;
        checks?: CheckItem[];
      };
      setRuntimeMode(data.mode ?? "dry-run");
      setRuntimeDataPath(data.data_path ?? "-");
      setRuntimeAiProvider(data.ai_provider ?? "deterministic");
      setRuntimeOpenAiModel(data.openai_model ?? "gpt-4o-mini");
      setRuntimeAnthropicModel(data.anthropic_model ?? "claude-3-5-haiku-latest");
      setRuntimeGeminiModel(data.gemini_model ?? "gemini-1.5-flash");
      setRuntimeAlibabaModelReasoning(data.alibaba_model_reasoning ?? "kimi-k2.5");
      setRuntimeFallbackOrder(data.ai_fallback_order ?? "anthropic,gemini,alibaba,deterministic");
      setRuntimeTimeoutSeconds(typeof data.ai_timeout_seconds === "number" ? data.ai_timeout_seconds : 20);
      setRuntimeBudgetUsd(typeof data.ai_budget_usd_per_run === "number" ? data.ai_budget_usd_per_run : 0.25);
      setRuntimeMaxRemoteCalls(typeof data.ai_max_remote_calls === "number" ? data.ai_max_remote_calls : 40);
      setRuntimeChecks(Array.isArray(data.checks) ? data.checks : []);
      setMessage("Runtime status refreshed.");
    } catch {
      setMessage("Cannot reach backend setup status API.");
    } finally {
      setBusy("idle");
    }
  };

  const runValidateDraft = async (): Promise<"ok" | "warn" | "error"> => {
    setBusy("validate");
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
          ai_provider: draft.aiProvider,
          openai_api_key: draft.openaiApiKey,
          openai_model: draft.openaiModel,
          openai_model_coder: draft.openaiModelCoder,
          openai_model_writing: draft.openaiModelWriting,
          anthropic_api_key: draft.anthropicApiKey,
          anthropic_model: draft.anthropicModel,
          anthropic_model_coder: draft.anthropicModelCoder,
          anthropic_model_writing: draft.anthropicModelWriting,
          gemini_api_key: draft.geminiApiKey,
          gemini_model: draft.geminiModel,
          gemini_model_coder: draft.geminiModelCoder,
          gemini_model_writing: draft.geminiModelWriting,
          alibaba_api_key: draft.alibabaApiKey,
          alibaba_base_url: draft.alibabaBaseUrl,
          alibaba_model_coder: draft.alibabaModelCoder,
          alibaba_model_reasoning: draft.alibabaModelReasoning,
          alibaba_model_writing: draft.alibabaModelWriting,
          ai_fallback_order: draft.aiFallbackOrder,
          ai_timeout_seconds: draft.aiTimeoutSeconds,
          ai_budget_usd_per_run: draft.aiBudgetUsdPerRun,
          ai_max_remote_calls: draft.aiMaxRemoteCalls,
          ai_model_path: draft.aiModelPath,
        }),
      });
      const data = (await res.json()) as { checks?: CheckItem[]; valid?: boolean };
      setValidateChecks(Array.isArray(data.checks) ? data.checks : []);
      return data.valid ? "ok" : "warn";
    } catch {
      return "error";
    } finally {
      setBusy("idle");
    }
  };

  const validateDraft = async () => {
    setMessage("");
    const result = await runValidateDraft();
    if (result === "ok") {
      setMessage("Validation passed.");
      return;
    }
    if (result === "warn") {
      setMessage("Validation finished with warnings.");
      return;
    }
    setMessage("Validation request failed.");
  };

  const applyDraft = async () => {
    setMessage("");
    saveDraftLocal();
    const result = await runValidateDraft();
    if (result === "ok") {
      setMessage("Draft applied and validation passed.");
      return;
    }
    if (result === "warn") {
      setMessage("Draft applied with validation warnings.");
      return;
    }
    setMessage("Draft saved, but validation request failed.");
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

  const probeExternal = async () => {
    setBusy("probe");
    setMessage("");
    try {
      const res = await fetch(`${API_BASE}/setup/probe-external`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const data = (await res.json()) as { checks?: CheckItem[]; all_ready?: boolean };
      setProbeChecks(Array.isArray(data.checks) ? data.checks : []);
      setMessage(data.all_ready ? "External probe passed." : "External probe completed with warnings.");
    } catch {
      setMessage("External probe request failed.");
    } finally {
      setBusy("idle");
    }
  };

  const createProfile = async () => {
    if (!profileName || profilePassphrase.length < 8) {
      setProfileMsg("Profile name and passphrase >= 8 chars are required.");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/setup/profiles/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          profile_name: profileName,
          passphrase: profilePassphrase,
          set_active: true,
          config: {
            trading_mode: draft.tradingMode,
            duckdb_path: draft.duckdbPath,
            vnstock_api_key: draft.vnstockApiKey,
            ssi_consumer_id: draft.ssiConsumerId,
            ssi_consumer_secret: draft.ssiConsumerSecret,
            ssi_account_no: draft.ssiAccountNo,
            ssi_private_key_b64: draft.ssiPrivateKeyB64,
            agent_ai_provider: draft.aiProvider,
            openai_api_key: draft.openaiApiKey,
            openai_model: draft.openaiModel,
            openai_model_coder: draft.openaiModelCoder,
            openai_model_writing: draft.openaiModelWriting,
            anthropic_api_key: draft.anthropicApiKey,
            anthropic_model: draft.anthropicModel,
            anthropic_model_coder: draft.anthropicModelCoder,
            anthropic_model_writing: draft.anthropicModelWriting,
            gemini_api_key: draft.geminiApiKey,
            gemini_model: draft.geminiModel,
            gemini_model_coder: draft.geminiModelCoder,
            gemini_model_writing: draft.geminiModelWriting,
            alibaba_api_key: draft.alibabaApiKey,
            alibaba_base_url: draft.alibabaBaseUrl,
            alibaba_model_coder: draft.alibabaModelCoder,
            alibaba_model_reasoning: draft.alibabaModelReasoning,
            alibaba_model_writing: draft.alibabaModelWriting,
            agent_ai_fallback_order: draft.aiFallbackOrder,
            agent_ai_timeout_seconds: draft.aiTimeoutSeconds,
            agent_ai_budget_usd_per_run: draft.aiBudgetUsdPerRun,
            agent_ai_max_remote_calls: draft.aiMaxRemoteCalls,
            ai_model_path: draft.aiModelPath,
          },
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      setProfileMsg("Profile created and encrypted.");
      setProfilePassphrase("");
      await fetchProfiles();
    } catch {
      setProfileMsg("Create profile failed.");
    }
  };

  const activateProfile = async (name: string) => {
    try {
      const res = await fetch(`${API_BASE}/setup/profiles/activate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile_name: name }),
      });
      if (!res.ok) throw new Error(await res.text());
      setProfileMsg(`Activated profile: ${name}`);
      await fetchProfiles();
    } catch {
      setProfileMsg("Activate profile failed.");
    }
  };

  const exportProfile = async (name: string) => {
    try {
      const res = await fetch(`${API_BASE}/setup/profiles/${name}/export`);
      const data = (await res.json()) as { payload_b64?: string };
      if (!res.ok || !data.payload_b64) throw new Error("Export failed");
      await navigator.clipboard.writeText(data.payload_b64);
      setProfileMsg(`Exported ${name} to clipboard.`);
    } catch {
      setProfileMsg("Export failed.");
    }
  };

  const importProfile = async () => {
    if (!profileName || !importPayload) {
      setProfileMsg("Profile name and payload are required for import.");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/setup/profiles/import`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          profile_name: profileName,
          payload_b64: importPayload,
          set_active: true,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      setProfileMsg(`Imported profile: ${profileName}`);
      setImportPayload("");
      await fetchProfiles();
    } catch {
      setProfileMsg("Import failed.");
    }
  };

  const rotateProfile = async () => {
    if (!activeProfile) {
      setProfileMsg("No active profile to rotate.");
      return;
    }
    if (rotateOldPass.length < 8 || rotateNewPass.length < 8) {
      setProfileMsg("Old/new passphrase must be >= 8 chars.");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/setup/profiles/rotate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          profile_name: activeProfile,
          old_passphrase: rotateOldPass,
          new_passphrase: rotateNewPass,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      setRotateOldPass("");
      setRotateNewPass("");
      setProfileMsg("Passphrase rotated.");
      await fetchProfiles();
    } catch {
      setProfileMsg("Rotate passphrase failed.");
    }
  };

  const revokeProfile = async (name: string) => {
    try {
      const res = await fetch(`${API_BASE}/setup/profiles/revoke`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile_name: name }),
      });
      if (!res.ok) throw new Error(await res.text());
      setProfileMsg(`Revoked profile: ${name}`);
      await fetchProfiles();
    } catch {
      setProfileMsg("Revoke profile failed.");
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
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span
            className={`rounded border px-2 py-1 text-[11px] font-semibold ${
              isDraftDirty
                ? "border-amber-800/60 bg-amber-900/20 text-amber-200"
                : "border-emerald-800/60 bg-emerald-900/20 text-emerald-300"
            }`}
          >
            {isDraftDirty ? "Unsaved changes" : "Saved"}
          </span>
          {lastSavedAt && <span className="text-[11px] text-zinc-500">Last saved: {lastSavedAt}</span>}
          <button
            onClick={saveDraftLocal}
            disabled={busy !== "idle" || !isDraftDirty}
            className="rounded bg-blue-700 px-3 py-1.5 text-[11px] font-semibold text-white disabled:opacity-50"
          >
            Save Draft
          </button>
          <button
            onClick={applyDraft}
            disabled={busy !== "idle"}
            className="rounded bg-emerald-700 px-3 py-1.5 text-[11px] font-semibold text-white disabled:opacity-50"
          >
            {busy === "validate" ? "Applying..." : "Apply Draft"}
          </button>
          <button
            onClick={resetToSavedDraft}
            disabled={busy !== "idle" || !isDraftDirty}
            className="rounded bg-zinc-700 px-3 py-1.5 text-[11px] font-semibold text-zinc-100 disabled:opacity-50"
          >
            Revert
          </button>
        </div>
      </div>

      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h2 className="mb-3 text-sm font-medium text-zinc-300">Step 2 — Key Input (local draft)</h2>
        <p className="mb-3 text-xs text-zinc-500">
          Draft is edited locally first. Use `Save Draft`/`Apply Draft` above for explicit actions. For secure persistent save, use Step 4 (Create Encrypted Profile).
        </p>
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
          <select
            value={draft.aiProvider}
            onChange={(e) => updateDraft("aiProvider", e.target.value as AiProvider)}
            className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100"
          >
            <option value="deterministic">AGENT_AI_PROVIDER=deterministic</option>
            <option value="openvino">AGENT_AI_PROVIDER=openvino</option>
            <option value="openai">AGENT_AI_PROVIDER=openai</option>
            <option value="anthropic">AGENT_AI_PROVIDER=anthropic</option>
            <option value="gemini">AGENT_AI_PROVIDER=gemini</option>
            <option value="alibaba">AGENT_AI_PROVIDER=alibaba</option>
          </select>
          <div className="rounded border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-zinc-400 sm:col-span-2">
            Task routing recommendation: `coder` for code/refactor, `reasoning` for analysis/plan/risk, `writing` for CSS/UI/docs.
          </div>
          {draft.aiProvider === "openai" && (
            <>
              <input
                value={draft.openaiModel}
                onChange={(e) => updateDraft("openaiModel", e.target.value)}
                placeholder="OPENAI_MODEL_REASONING (e.g. gpt-4o-mini)"
                className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500"
              />
              <input
                value={draft.openaiModelCoder}
                onChange={(e) => updateDraft("openaiModelCoder", e.target.value)}
                placeholder="OPENAI_MODEL_CODER"
                className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500"
              />
              <input
                value={draft.openaiModelWriting}
                onChange={(e) => updateDraft("openaiModelWriting", e.target.value)}
                placeholder="OPENAI_MODEL_WRITING"
                className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 sm:col-span-2"
              />
              <input
                value={draft.openaiApiKey}
                onChange={(e) => updateDraft("openaiApiKey", e.target.value)}
                placeholder="OPENAI_API_KEY"
                className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 sm:col-span-2"
              />
            </>
          )}
          {draft.aiProvider === "anthropic" && (
            <>
              <input
                value={draft.anthropicModel}
                onChange={(e) => updateDraft("anthropicModel", e.target.value)}
                placeholder="ANTHROPIC_MODEL_REASONING"
                className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500"
              />
              <input
                value={draft.anthropicModelCoder}
                onChange={(e) => updateDraft("anthropicModelCoder", e.target.value)}
                placeholder="ANTHROPIC_MODEL_CODER"
                className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500"
              />
              <input
                value={draft.anthropicModelWriting}
                onChange={(e) => updateDraft("anthropicModelWriting", e.target.value)}
                placeholder="ANTHROPIC_MODEL_WRITING"
                className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 sm:col-span-2"
              />
              <input
                value={draft.anthropicApiKey}
                onChange={(e) => updateDraft("anthropicApiKey", e.target.value)}
                placeholder="ANTHROPIC_API_KEY"
                className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 sm:col-span-2"
              />
            </>
          )}
          {draft.aiProvider === "gemini" && (
            <>
              <input
                value={draft.geminiModel}
                onChange={(e) => updateDraft("geminiModel", e.target.value)}
                placeholder="GEMINI_MODEL_REASONING"
                className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500"
              />
              <input
                value={draft.geminiModelCoder}
                onChange={(e) => updateDraft("geminiModelCoder", e.target.value)}
                placeholder="GEMINI_MODEL_CODER"
                className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500"
              />
              <input
                value={draft.geminiModelWriting}
                onChange={(e) => updateDraft("geminiModelWriting", e.target.value)}
                placeholder="GEMINI_MODEL_WRITING"
                className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 sm:col-span-2"
              />
              <input
                value={draft.geminiApiKey}
                onChange={(e) => updateDraft("geminiApiKey", e.target.value)}
                placeholder="GEMINI_API_KEY"
                className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 sm:col-span-2"
              />
            </>
          )}
          {draft.aiProvider === "alibaba" && (
            <>
              <input
                value={draft.alibabaBaseUrl}
                onChange={(e) => updateDraft("alibabaBaseUrl", e.target.value)}
                placeholder="ALIBABA_BASE_URL"
                className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 sm:col-span-2"
              />
              <input
                value={draft.alibabaApiKey}
                onChange={(e) => updateDraft("alibabaApiKey", e.target.value)}
                placeholder="ALIBABA_API_KEY"
                className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 sm:col-span-2"
              />
              <input
                value={draft.alibabaModelCoder}
                onChange={(e) => updateDraft("alibabaModelCoder", e.target.value)}
                placeholder="ALIBABA_MODEL_CODER (qwen2.5-coder-32b-instruct)"
                className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500"
              />
              <input
                value={draft.alibabaModelReasoning}
                onChange={(e) => updateDraft("alibabaModelReasoning", e.target.value)}
                placeholder="ALIBABA_MODEL_REASONING (kimi-k2.5)"
                className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500"
              />
              <input
                value={draft.alibabaModelWriting}
                onChange={(e) => updateDraft("alibabaModelWriting", e.target.value)}
                placeholder="ALIBABA_MODEL_WRITING (minimax-m2.5)"
                className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 sm:col-span-2"
              />
            </>
          )}
          <input
            value={draft.aiFallbackOrder}
            onChange={(e) => updateDraft("aiFallbackOrder", e.target.value)}
            placeholder="AGENT_AI_FALLBACK_ORDER (e.g. anthropic,gemini,deterministic)"
            className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 sm:col-span-2"
          />
          <input
            type="number"
            min={3}
            max={120}
            step={1}
            value={draft.aiTimeoutSeconds}
            onChange={(e) => updateDraft("aiTimeoutSeconds", Number(e.target.value) || 20)}
            placeholder="AGENT_AI_TIMEOUT_SECONDS"
            className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500"
          />
          <input
            type="number"
            min={0.01}
            max={50}
            step={0.01}
            value={draft.aiBudgetUsdPerRun}
            onChange={(e) => updateDraft("aiBudgetUsdPerRun", Number(e.target.value) || 0.25)}
            placeholder="AGENT_AI_BUDGET_USD_PER_RUN"
            className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500"
          />
          <input
            type="number"
            min={1}
            max={400}
            step={1}
            value={draft.aiMaxRemoteCalls}
            onChange={(e) => updateDraft("aiMaxRemoteCalls", Number(e.target.value) || 40)}
            placeholder="AGENT_AI_MAX_REMOTE_CALLS"
            className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 sm:col-span-2"
          />
          <input
            value={draft.aiModelPath}
            onChange={(e) => updateDraft("aiModelPath", e.target.value)}
            placeholder="OPENVINO_MODEL_PATH"
            className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 sm:col-span-2"
          />
          <div className="rounded border border-zinc-800 bg-zinc-950 p-3 text-xs text-zinc-400 sm:col-span-2">
            <div className="mb-2 font-semibold uppercase tracking-wider text-zinc-500">Role-model recommendation matrix</div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] border-collapse">
                <thead>
                  <tr className="text-left text-[11px] text-zinc-500">
                    <th className="border-b border-zinc-800 px-2 py-1">Task</th>
                    <th className="border-b border-zinc-800 px-2 py-1">Role</th>
                    <th className="border-b border-zinc-800 px-2 py-1">Goal</th>
                    <th className="border-b border-zinc-800 px-2 py-1">OpenAI</th>
                    <th className="border-b border-zinc-800 px-2 py-1">Anthropic</th>
                    <th className="border-b border-zinc-800 px-2 py-1">Gemini</th>
                    <th className="border-b border-zinc-800 px-2 py-1">Alibaba</th>
                  </tr>
                </thead>
                <tbody>
                  {(modelRecommendations.length > 0 ? modelRecommendations : []).map((row) => (
                    <tr key={`${row.role}-${row.task}`} className="text-[11px]">
                      <td className="border-b border-zinc-900 px-2 py-1 text-zinc-300">{row.task}</td>
                      <td className="border-b border-zinc-900 px-2 py-1 text-zinc-400">{row.role}</td>
                      <td className="border-b border-zinc-900 px-2 py-1 text-zinc-500">{row.goal}</td>
                      <td className="border-b border-zinc-900 px-2 py-1">{row.openai}</td>
                      <td className="border-b border-zinc-900 px-2 py-1">{row.anthropic}</td>
                      <td className="border-b border-zinc-900 px-2 py-1">{row.gemini}</td>
                      <td className="border-b border-zinc-900 px-2 py-1">{row.alibaba}</td>
                    </tr>
                  ))}
                  {modelRecommendations.length === 0 && (
                    <tr>
                      <td className="px-2 py-2 text-zinc-500" colSpan={7}>
                        Recommendation matrix unavailable (backend offline). You can still configure models manually.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
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
          <button
            onClick={probeExternal}
            disabled={busy !== "idle"}
            className="rounded bg-violet-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
          >
            {busy === "probe" ? "Probing..." : "Probe External Connections"}
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
              <div>Agent AI provider: {runtimeAiProvider}</div>
              <div>AI model: {runtimeAiModel}</div>
              <div>Failover order: {runtimeFallbackOrder}</div>
              <div>Timeout: {runtimeTimeoutSeconds}s</div>
              <div>Budget: ${runtimeBudgetUsd.toFixed(2)}/run</div>
              <div>Max remote calls: {runtimeMaxRemoteCalls}</div>
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
        <div className="mt-4 space-y-2">
          <div className="text-xs font-semibold uppercase tracking-wider text-zinc-500">External probe</div>
          <div className="space-y-2">
            {probeChecks.length === 0 && (
              <div className="rounded border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-zinc-500">
                Run Probe External Connections to test SSI/VNStock/AI runtime availability.
              </div>
            )}
            {probeChecks.map((item) => (
              <div key={`probe-${item.name}`} className={`rounded border px-3 py-2 text-xs ${statusClass(item.status)}`}>
                <div className="font-semibold">{item.name}</div>
                <div className="opacity-90">{item.detail}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h2 className="mb-3 text-sm font-medium text-zinc-300">Step 4 — Secure Profile Vault</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <input
            value={profileName}
            onChange={(e) => setProfileName(e.target.value)}
            placeholder="Profile name"
            className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100"
          />
          <input
            type="password"
            value={profilePassphrase}
            onChange={(e) => setProfilePassphrase(e.target.value)}
            placeholder="Passphrase (>=8)"
            className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100"
          />
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={createProfile}
            className="rounded bg-emerald-700 px-3 py-2 text-xs font-semibold text-white"
          >
            Create Encrypted Profile
          </button>
          <button
            type="button"
            onClick={importProfile}
            className="rounded bg-blue-700 px-3 py-2 text-xs font-semibold text-white"
          >
            Import Profile
          </button>
          <button
            type="button"
            onClick={rotateProfile}
            className="rounded bg-zinc-700 px-3 py-2 text-xs font-semibold text-zinc-100"
          >
            Rotate Passphrase
          </button>
        </div>

        <textarea
          value={importPayload}
          onChange={(e) => setImportPayload(e.target.value)}
          placeholder="Paste exported payload_b64 to import profile"
          className="mt-3 min-h-20 w-full rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-xs text-zinc-100"
        />
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <input
            type="password"
            value={rotateOldPass}
            onChange={(e) => setRotateOldPass(e.target.value)}
            placeholder="Old passphrase (active profile)"
            className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-xs text-zinc-100"
          />
          <input
            type="password"
            value={rotateNewPass}
            onChange={(e) => setRotateNewPass(e.target.value)}
            placeholder="New passphrase"
            className="rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-xs text-zinc-100"
          />
        </div>

        <div className="mt-4 rounded border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-zinc-300">
          Active profile: {activeProfile ?? "none"}
        </div>
        <div className="mt-3 space-y-2">
          {profiles.length === 0 && (
            <div className="rounded border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-zinc-500">
              No profiles found.
            </div>
          )}
          {profiles.map((profile) => (
            <div key={profile.name} className="flex flex-wrap items-center justify-between gap-2 rounded border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs">
              <div>
                <div className="font-semibold text-zinc-200">
                  {profile.name} {profile.revoked ? "(revoked)" : ""}
                </div>
                <div className="text-zinc-500">{profile.file}</div>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => void activateProfile(profile.name)}
                  disabled={profile.revoked}
                  className="rounded border border-emerald-700 px-2 py-1 text-xs text-emerald-400 disabled:opacity-40"
                >
                  Activate
                </button>
                <button
                  type="button"
                  onClick={() => void exportProfile(profile.name)}
                  disabled={profile.revoked}
                  className="rounded border border-blue-700 px-2 py-1 text-xs text-blue-400 disabled:opacity-40"
                >
                  Export
                </button>
                <button
                  type="button"
                  onClick={() => void revokeProfile(profile.name)}
                  className="rounded border border-red-700 px-2 py-1 text-xs text-red-400"
                >
                  Revoke
                </button>
              </div>
            </div>
          ))}
        </div>
        {profileMsg && <p className="mt-2 text-xs text-zinc-400">{profileMsg}</p>}
      </div>
    </div>
  );
}
