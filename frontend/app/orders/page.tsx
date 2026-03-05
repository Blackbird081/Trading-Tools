import { TradingErrorBoundary } from "@/components/error-boundary";
import { RuntimeSafetyBadges } from "@/components/runtime-safety-badges";
import { OrderForm } from "./_components/order-form";
import { OrderHistory } from "./_components/order-history";

export default function OrdersPage() {
  return (
    <TradingErrorBoundary>
      <div className="p-3 sm:p-4">
        <div className="mb-4 space-y-2">
          <h1 className="text-xl font-semibold sm:text-2xl">Order Management</h1>
          <p className="text-xs text-zinc-500">Runtime safety status must be visible before placing dry-run/live orders.</p>
          <RuntimeSafetyBadges />
        </div>
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <TradingErrorBoundary>
            <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-3 sm:p-4">
              <h2 className="mb-3 text-sm font-medium text-zinc-400">Đặt lệnh</h2>
              <OrderForm />
            </div>
          </TradingErrorBoundary>
          <TradingErrorBoundary>
            <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-3 sm:p-4">
              <h2 className="mb-3 text-sm font-medium text-zinc-400">Lịch sử lệnh</h2>
              <OrderHistory />
            </div>
          </TradingErrorBoundary>
        </div>
      </div>
    </TradingErrorBoundary>
  );
}
