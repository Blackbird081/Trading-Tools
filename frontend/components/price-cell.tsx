import { cn } from "@/lib/utils";

interface PriceCellProps {
  value: number | null | undefined;
  change?: number;
  isCeiling?: boolean;
  isFloor?: boolean;
}

export function PriceCell({ value, change, isCeiling, isFloor }: PriceCellProps) {
  if (value == null) {
    return <span className="text-zinc-600">—</span>;
  }

  return (
    <span
      className={cn(
        "font-mono text-sm tabular-nums",
        isCeiling && "text-fuchsia-400",
        isFloor && "text-cyan-400",
        !isCeiling &&
          !isFloor &&
          change !== undefined &&
          change > 0 &&
          "text-emerald-400",
        !isCeiling &&
          !isFloor &&
          change !== undefined &&
          change < 0 &&
          "text-rose-400",
        !isCeiling &&
          !isFloor &&
          (change === undefined || change === 0) &&
          "text-amber-400"
      )}
    >
      {value.toFixed(2)}
    </span>
  );
}
