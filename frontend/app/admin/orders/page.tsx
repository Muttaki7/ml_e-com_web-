"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { adminApi, formatMoney, getApiError, downloadBlob } from "@/lib/api";
import { useAdminAuth } from "@/lib/useAdminAuth";
import { AdminShell } from "@/components/AdminShell";
import toast from "react-hot-toast";
import { FileText, Filter } from "lucide-react";

const ORDER_STATUSES = [
  "pending",
  "confirmed",
  "processing",
  "packed",
  "shipped",
  "out_for_delivery",
  "delivered",
  "cancelled",
  "returned",
  "refunded",
];

const STATUS_STYLES: Record<string, string> = {
  delivered: "bg-emerald-100 text-emerald-700",
  cancelled: "bg-rose-100 text-rose-700",
  returned: "bg-rose-100 text-rose-700",
  refunded: "bg-slate-200 text-slate-700",
};

export default function AdminOrdersPage() {
  const router = useRouter();
  const { user, loading } = useAdminAuth();
  const [orders, setOrders] = useState<any[]>([]);
  const [status, setStatus] = useState("");
  const statusRef = useRef("");

  useEffect(() => {
    if (!loading) load(statusRef.current);
    const timer = setInterval(() => load(statusRef.current), 5 * 60 * 1000);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading]);

  async function load(filter?: string) {
    try {
      const params: any = { limit: 100 };
      if (filter) params.status = filter;
      const r = await adminApi.orders(params);
      setOrders(r.data || []);
    } catch (e: any) {
      if (e.response?.status === 403) router.replace("/admin/login");
      setOrders([]);
    }
  }

  async function changeStatus(id: string, newStatus: string) {
    try {
      await adminApi.updateOrderStatus(id, newStatus);
      toast.success(`Order marked ${newStatus}`);
      load(status);
    } catch (e: any) {
      toast.error(getApiError(e, "Update failed"));
    }
  }

  async function downloadInvoice(id: string, orderNumber: string) {
    try {
      const r = await adminApi.orderInvoice(id);
      downloadBlob(r, `INV-${orderNumber}.pdf`);
    } catch (e: any) {
      toast.error(getApiError(e, "Invoice download failed"));
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-100 dark:bg-slate-950 flex items-center justify-center">
        <div className="w-16 h-16 rounded-xl bg-slate-200 dark:bg-slate-800 animate-pulse" />
      </div>
    );
  }

  return (
    <AdminShell title="Orders" user={user}>
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <div className="relative">
          <Filter size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              statusRef.current = e.target.value;
              load(e.target.value);
            }}
            className="input !py-2 !pl-9 text-sm"
          >
            <option value="">All statuses</option>
            {ORDER_STATUSES.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500 dark:text-slate-400 border-b dark:border-slate-700">
              <th className="py-3 px-4">Order #</th>
              <th>Date</th>
              <th>Method</th>
              <th>Payment</th>
              <th>Total</th>
              <th>Status</th>
              <th className="pr-4">Actions</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((o) => (
              <tr
                key={o.id}
                className="border-b dark:border-slate-700 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-800/50"
              >
                <td className="py-3 px-4 font-medium text-slate-900 dark:text-white">{o.order_number}</td>
                <td className="text-slate-600 dark:text-slate-400">{o.created_at?.slice(0, 10)}</td>
                <td>
                  <span className="uppercase text-xs bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 rounded px-2 py-0.5">
                    {o.payment_method}
                  </span>
                </td>
                <td className="text-slate-600 dark:text-slate-400">{o.payment_status}</td>
                <td className="font-semibold text-slate-900 dark:text-white">{formatMoney(o.total)}</td>
                <td>
                  <span
                    className={`inline-block px-2 py-0.5 rounded-full text-xs ${
                      STATUS_STYLES[o.status] || "bg-amber-100 text-amber-700"
                    }`}
                  >
                    {o.status}
                  </span>
                </td>
                <td className="pr-4 py-3">
                  <div className="flex items-center gap-2">
                    <select
                      value={o.status}
                      onChange={(e) => changeStatus(o.id, e.target.value)}
                      className="border dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 rounded-lg px-2 py-1 text-xs"
                    >
                      {ORDER_STATUSES.map((s) => (
                        <option key={s}>{s}</option>
                      ))}
                    </select>
                    <button
                      onClick={() => downloadInvoice(o.id, o.order_number || o.id)}
                      className="inline-flex items-center gap-1 px-2 py-1 rounded-lg border dark:border-slate-700 text-xs whitespace-nowrap hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300"
                      title="Download invoice (.pdf)"
                    >
                      <FileText size={13} /> Invoice
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {orders.length === 0 && (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-400">
                  No orders found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </AdminShell>
  );
}