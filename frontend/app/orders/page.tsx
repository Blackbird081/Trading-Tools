import { TradingErrorBoundary } from "@/components/error-boundary";
import { OrderForm } from "./_components/order-form";
import { OrderHistory } from "./_components/order-history";

export default function OrdersPage() {
  return (
    <TradingErrorBoundary>
      <div className="p-3 sm:p-4">
        <h1 className="mb-4 text-xl font-semibold sm:text-2xl">Order Management</h1>
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <TradingErrorBoundary>
            <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-3 sm:p-4">
              <h2 className="text-sm font-medium text-zinc-400 mb-3">Đặt lệnh</h2>
              <OrderForm />
            </div>
          </TradingErrorBoundary>
          <TradingErrorBoundary>
            <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-3 sm:p-4">
              <h2 className="text-sm font-medium text-zinc-400 mb-3">Lịch sử lệnh</h2>
              <OrderHistory />
            </div>
          </TradingErrorBoundary>
        </div>
      </div>
    </TradingErrorBoundary>
  );
}
