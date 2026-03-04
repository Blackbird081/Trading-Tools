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
  const [profiles, setProfiles] = useState<ProfileInfo[]>([]);
  const [activeProfile, setActiveProfile] = useState<string | null>(null);
  const [profileName, setProfileName] = useState("default");
  const [profilePassphrase, setProfilePassphrase] = useState("");
  const [profileMsg, setProfileMsg] = useState("");
  const [importPayload, setImportPayload] = useState("");
  const [rotateOldPass, setRotateOldPass] = useState("");
  const [rotateNewPass, setRotateNewPass] = useState("");

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
