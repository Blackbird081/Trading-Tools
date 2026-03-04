import { create } from "zustand";
import { subscribeWithSelector } from "zustand/middleware";
import type { OrderData } from "@/types/market";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

interface OrderState {
  orders: OrderData[];
  loading: boolean;
  error: string | null;

  fetchOrders: () => Promise<void>;
  placeOrder: (payload: {
    symbol: string;
    side: "BUY" | "SELL";
    orderType: "LO" | "ATO" | "ATC" | "MP";
    quantity: number;
    price: number;
    mode?: "dry-run" | "live";
    idempotencyKey?: string;
    confirmToken?: string;
  }) => Promise<{ ok: boolean; message: string; confirmToken?: string }>;
  cancelOrder: (id: string) => Promise<void>;
  addOrder: (order: OrderData) => void;
  updateOrder: (id: string, update: Partial<OrderData>) => void;
  getOpenOrders: () => OrderData[];
}

function mapStatus(raw: string): OrderData["status"] {
  if (raw === "MATCHED") return "MATCHED";
  if (raw === "CANCELLED") return "CANCELLED";
  if (raw === "PARTIAL_FILL") return "PARTIAL";
  if (raw === "PENDING" || raw === "CREATED") return "PENDING";
  return "REJECTED";
}

function mapOrder(row: Record<string, unknown>): OrderData {
  return {
    id: String(row.order_id ?? ""),
    symbol: String(row.symbol ?? ""),
    side: (String(row.side ?? "BUY") as OrderData["side"]),
    type: (String(row.order_type ?? "LO") as OrderData["type"]),
    price: Number(row.req_price ?? 0),
    quantity: Number(row.quantity ?? 0),
    filledQty: Number(row.filled_quantity ?? 0),
    status: mapStatus(String(row.status ?? "PENDING")),
    createdAt: new Date(String(row.created_at ?? Date.now())).getTime(),
    brokerOrderId: row.broker_order_id ? String(row.broker_order_id) : null,
    rejectionReason: row.rejection_reason ? String(row.rejection_reason) : null,
    mode: (String(row.mode ?? "dry-run") as OrderData["mode"]),
  };
}

export const useOrderStore = create<OrderState>()(
  subscribeWithSelector((set, get) => ({
    orders: [],
    loading: false,
    error: null,

    fetchOrders: async () => {
      set({ loading: true, error: null });
      try {
        const res = await fetch(`${API_BASE}/orders?limit=200`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = (await res.json()) as { orders?: Record<string, unknown>[] };
        const orders = (data.orders ?? []).map(mapOrder);
        set({ orders, loading: false });
      } catch (err) {
        set({ loading: false, error: err instanceof Error ? err.message : "Cannot fetch orders" });
      }
    },

    placeOrder: async (payload) => {
      const body = {
        symbol: payload.symbol,
        side: payload.side,
        order_type: payload.orderType,
        quantity: payload.quantity,
        price: payload.price,
        idempotency_key: payload.idempotencyKey ?? `ui-${Date.now()}-${payload.symbol}-${payload.side}`,
        mode: payload.mode ?? "dry-run",
        confirm_token: payload.confirmToken ?? null,
      };
      try {
        const res = await fetch(`${API_BASE}/orders`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!res.ok) {
          const errText = await res.text();
          throw new Error(errText || `HTTP ${res.status}`);
        }
        const data = (await res.json()) as {
          success?: boolean;
          message?: string;
          requires_confirmation?: boolean;
          confirm_token?: string;
        };
        if (data.requires_confirmation && data.confirm_token) {
          return {
            ok: false,
            message: data.message ?? "Live mode requires confirmation",
            confirmToken: data.confirm_token,
          };
        }
        await get().fetchOrders();
        return { ok: Boolean(data.success), message: data.success ? "Order placed" : "Order rejected" };
      } catch (err) {
        set({ error: err instanceof Error ? err.message : "Place order failed" });
        return { ok: false, message: err instanceof Error ? err.message : "Place order failed" };
      }
    },

    cancelOrder: async (id) => {
      try {
        const res = await fetch(`${API_BASE}/orders/${id}/cancel`, { method: "POST" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        await get().fetchOrders();
      } catch (err) {
        set({ error: err instanceof Error ? err.message : "Cancel order failed" });
      }
    },

    addOrder: (order) =>
      set((state) => ({
        orders: [order, ...state.orders],
      })),

    updateOrder: (id, update) =>
      set((state) => ({
        orders: state.orders.map((o) =>
          o.id === id ? { ...o, ...update } : o
        ),
      })),

    getOpenOrders: () =>
      get().orders.filter(
        (o) =>
          o.status === "PENDING" ||
          o.status === "PARTIAL"
      ),
  }))
);
