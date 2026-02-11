import { create } from "zustand";
import { subscribeWithSelector } from "zustand/middleware";
import type { OrderData } from "@/types/market";

interface OrderState {
  orders: OrderData[];

  addOrder: (order: OrderData) => void;
  updateOrder: (id: string, update: Partial<OrderData>) => void;
  getOpenOrders: () => OrderData[];
}

export const useOrderStore = create<OrderState>()(
  subscribeWithSelector((set, get) => ({
    orders: [],

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
