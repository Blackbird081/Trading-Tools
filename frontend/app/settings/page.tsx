export default function SettingsPage() {
  return (
    <div className="p-4">
      <h1 className="text-lg font-semibold mb-4">Settings</h1>
      <div className="space-y-4">
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <h2 className="text-sm font-medium text-zinc-400 mb-2">Connection</h2>
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-emerald-400" />
            <span className="text-sm text-zinc-300">WebSocket: Connected</span>
          </div>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <h2 className="text-sm font-medium text-zinc-400 mb-2">API Keys</h2>
          <p className="text-sm text-zinc-500">SSI FastConnect credentials managed via .env</p>
        </div>
      </div>
    </div>
  );
}
