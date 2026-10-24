"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { orderApi, formatMoney, getApiError, downloadBlob } from "@/lib/api";
import { StorefrontHeader } from "@/components/StorefrontHeader";
import { Footer } from "@/components/Footer";
import TwoFactorCard from "@/components/TwoFactorCard";
import toast from "react-hot-toast";
import { FileDown, ShoppingBag } from "lucide-react";

const STATUS_STYLES: Record<string, string> = {
  pending:
    "bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400",
  confirmed:
    "bg-blue-100 text-blue-700 dark:bg-blue-500/10 dark:text-blue-400",
  processing:
    "bg-indigo-100 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-400",
  shipped: "bg-cyan-100 text-cyan-700 dark:bg-cyan-500/10 dark:text-cyan-400",
  delivered:
    "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400",
  cancelled: "bg-rose-100 text-rose-700 dark:bg-rose-500/10 dark:text-rose-400",
  returned:
    "bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-300",
};

export default function MyOrdersPage() {
  const router = useRouter();
  const [orders, setOrders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const r = await orderApi.myOrders();
      setOrders(r.data || []);
    } catch (e: any) {
      if (e.response?.status === 401) router.replace("/login");
      else toast.error(getApiError(e, "Failed to load orders"));
      setOrders([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!localStorage.getItem("access_token")) {
      router.replace("/login");
      return;
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function downloadInvoice(order: any) {
    setDownloading(order.id);
    try {
      const r = await orderApi.myInvoice(order.id);
      downloadBlob(r, `INV-${order.order_number || order.id}.pdf`);
    } catch (e: any) {
      toast.error(getApiError(e, "Invoice download failed"));
    } finally {
      setDownloading(null);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col">
      <StorefrontHeader />

      <main className="max-w-4xl mx-auto px-4 py-8 w-full flex-1">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">My Account</h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
          Track your orders, download invoices, and manage account security.
        </p>

        <div className="mt-6">
          <TwoFactorCard scope="customer" />
        </div>

        <h2 className="mt-8 text-lg font-semibold text-slate-900 dark:text-white">My Orders</h2>

        {loading ? (
          <div className="mt-6 space-y-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-24 rounded-2xl bg-slate-100 dark:bg-slate-800 animate-pulse" />
            ))}
          </div>
        ) : orders.length === 0 ? (
          <div className="mt-8 card p-12 text-center">
            <ShoppingBag size={36} className="mx-auto text-slate-300 dark:text-slate-600" />
            <h2 className="text-lg font-semibold mt-3 text-slate-900 dark:text-white">No orders yet</h2>
            <p className="mt-2 text-slate-500 dark:text-slate-400 text-sm">
              Once you place an order it will appear here.
            </p>
            <Link
              href="/products"
              className="btn-primary inline-flex mt-6"
            >
              Start Shopping
            </Link>
          </div>
        ) : (
          <div className="mt-6 space-y-4">
            {orders.map((o) => (
              <div key={o.id} className="card p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-slate-900 dark:text-white">{o.order_number}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                      {o.created_at ? new Date(o.created_at).toLocaleString() : ""}
                    </p>
                  </div>
                  <span
                    className={`px-2.5 py-1 rounded-full text-xs font-medium capitalize ${
                      STATUS_STYLES[o.status] || "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                    }`}
                  >
                    {o.status}
                  </span>
                </div>

                {Array.isArray(o.items) && o.items.length > 0 && (
                  <ul className="mt-3 text-sm text-slate-600 dark:text-slate-400 space-y-1">
                    {o.items.map((it: any, idx: number) => (
                      <li key={idx} className="flex justify-between gap-3">
                        <span className="truncate">
                          {it.product_name || it.name} × {it.quantity ?? it.qty}
                        </span>
                        <span>{formatMoney(it.total_price ?? it.line_total ?? 0)}</span>
                      </li>
                    ))}
                  </ul>
                )}

                <div className="mt-4 pt-3 border-t dark:border-slate-700 flex flex-wrap items-center justify-between gap-3">
                  <div className="text-sm">
                    <span className="text-slate-500 dark:text-slate-400">Total </span>
                    <span className="font-bold text-sky-600 dark:text-sky-400">{formatMoney(o.total || 0)}</span>
                    {o.payment_method && (
                      <span className="text-slate-400 dark:text-slate-500 text-xs ml-2">
                        · {o.payment_method} {o.payment_status ? `(${o.payment_status})` : ""}
                      </span>
                    )}
                  </div>
                  <button
                    onClick={() => downloadInvoice(o)}
                    disabled={downloading === o.id}
                    className="btn-outline !text-sm !py-2 inline-flex"
                  >
                    <FileDown size={15} />
                    {downloading === o.id ? "Preparing…" : "Download Invoice (.pdf)"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}