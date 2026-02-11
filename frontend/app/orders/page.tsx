export default function OrdersPage() {
  return (
    <div className="p-4">
      <h1 className="text-lg font-semibold mb-4">Order Management</h1>
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <h2 className="text-sm font-medium text-zinc-400 mb-3">Order Form</h2>
          <p className="text-sm text-zinc-500">Order placement coming in Phase 5.</p>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <h2 className="text-sm font-medium text-zinc-400 mb-3">Order History</h2>
          <p className="text-sm text-zinc-500">No orders yet.</p>
        </div>
      </div>
    </div>
  );
}
