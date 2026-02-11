export interface TickData {
  symbol: string;
  price: number;
  change: number;
  changePct: number;
  volume: number;
  high: number;
  low: number;
  open: number;
  ceiling: number;
  floor: number;
  reference: number;
  timestamp: number;
}

export interface CandleData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

export interface AgentSignal {
  id: string;
  symbol: string;
  action: "BUY" | "SELL" | "HOLD";
  score: number;
  reason: string;
  timestamp: number;
}

export interface Position {
  symbol: string;
  quantity: number;
  avgPrice: number;
  marketPrice: number;
  pnl: number;
  pnlPct: number;
}

export interface OrderData {
  id: string;
  symbol: string;
  side: "BUY" | "SELL";
  type: "LO" | "ATO" | "ATC" | "MP";
  price: number;
  quantity: number;
  filledQty: number;
  status: "PENDING" | "MATCHED" | "PARTIAL" | "CANCELLED" | "REJECTED";
  createdAt: number;
}
