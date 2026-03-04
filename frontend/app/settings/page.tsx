import { SetupWizard } from "./_components/setup-wizard";

export default function SettingsPage() {
  return (
    <div className="p-4">
      <h1 className="mb-1 text-lg font-semibold">Setup Wizard</h1>
      <p className="mb-4 text-sm text-zinc-500">
        Local profile draft + runtime validation. Secrets in this step are kept client-side draft only.
      </p>
      <p className="mb-4 text-xs text-zinc-600">
        Developed by Tien - Tan Thuan Port @2026
      </p>
      <SetupWizard />
    </div>
  );
}
