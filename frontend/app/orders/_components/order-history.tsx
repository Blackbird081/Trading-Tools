"use client";

import { useOrderStore } from "@/stores/order-store";

export function OrderHistory() {
  const orders = useOrderStore((s) => s.orders);

  if (orders.length === 0) {
    return (
      <div className="p-8 text-center text-zinc-500">
        Chưa có lệnh nào
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-800 text-zinc-400">
            <th className="px-4 py-2 text-left">Mã CK</th>
            <th className="px-4 py-2 text-left">Loại</th>
            <th className="px-4 py-2 text-right">KL</th>
            <th className="px-4 py-2 text-right">Giá</th>
            <th className="px-4 py-2 text-center">Trạng thái</th>
            <th className="px-4 py-2 text-right">Thời gian</th>
          </tr>
        </thead>
        <tbody>
          {orders.map((order) => (
            <tr
              key={order.id}
              className="border-b border-zinc-800/50 hover:bg-zinc-800/30"
            >
              <td className="px-4 py-2 font-semibold text-amber-400">
                {order.symbol}
              </td>
              <td
                className={`px-4 py-2 ${
                  order.side === "BUY" ? "text-green-400" : "text-red-400"
                }`}
              >
                {order.side === "BUY" ? "MUA" : "BÁN"}
              </td>
              <td className="px-4 py-2 text-right">
                {order.quantity.toLocaleString()}
              </td>
              <td className="px-4 py-2 text-right">
                {order.price.toFixed(2)}
              </td>
              <td className="px-4 py-2 text-center">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs ${
                    order.status === "MATCHED"
                      ? "bg-green-900/50 text-green-400"
                      : order.status === "PENDING"
                        ? "bg-yellow-900/50 text-yellow-400"
                        : order.status === "REJECTED"
                          ? "bg-red-900/50 text-red-400"
                          : "bg-zinc-800 text-zinc-400"
                  }`}
                >
                  {order.status}
                </span>
              </td>
              <td className="px-4 py-2 text-right text-zinc-500 text-xs">
                {new Date(order.createdAt).toLocaleTimeString("vi-VN")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
