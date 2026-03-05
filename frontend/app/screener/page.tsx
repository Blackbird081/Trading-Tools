import { RuntimeSafetyBadges } from "@/components/runtime-safety-badges";
import { PipelineRunner } from "./_components/pipeline-runner";

export default function ScreenerPage() {
  return (
    <div className="h-full overflow-y-auto p-3 sm:p-4">
      <div className="mb-4 space-y-2">
        <h1 className="text-xl font-semibold sm:text-2xl">Screener</h1>
        <p className="text-xs text-zinc-500">Check dry-run/live mode and kill-switch before running the pipeline.</p>
        <RuntimeSafetyBadges />
      </div>
      <PipelineRunner />
    </div>
  );
}
