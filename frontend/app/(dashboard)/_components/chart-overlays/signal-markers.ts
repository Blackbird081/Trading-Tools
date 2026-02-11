import type { ISeriesApi, SeriesMarker, Time } from "lightweight-charts";

interface AgentSignalMarker {
  time: number;
  type: "BUY" | "SELL";
  reason: string;
  score: number;
}

export function applySignalMarkers(
  series: ISeriesApi<"Candlestick">,
  signals: AgentSignalMarker[]
): void {
  const markers: SeriesMarker<Time>[] = signals.map((s) => ({
    time: s.time as Time,
    position: s.type === "BUY" ? "belowBar" : "aboveBar",
    color: s.type === "BUY" ? "#34d399" : "#f87171",
    shape: s.type === "BUY" ? "arrowUp" : "arrowDown",
    text: `${s.type} (${s.score.toFixed(1)})`,
  }));

  series.setMarkers(markers);
}
