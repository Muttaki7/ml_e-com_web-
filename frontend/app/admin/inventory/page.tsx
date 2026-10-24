"use client";

import { useEffect, useState } from "react";
import { adminApi, formatMoney, getApiError } from "@/lib/api";
import { useAdminAuth } from "@/lib/useAdminAuth";
import { AdminShell } from "@/components/AdminShell";
import toast from "react-hot-toast";
import { PackagePlus } from "lucide-react";

export default function AdminInventoryPage() {
  const { user, loading } = useAdminAuth();
  const [items, setItems] = useState<any[]>([]);
  const [restock, setRestock] = useState<Record<string, number>>({});

  useEffect(() => {
    if (!loading) load();
  }, [loading]);

  async function load() {
    try {
      const r = await adminApi.products({ limit: 200 });
      setItems(r.data || []);
    } catch {
      setItems([]);
    }
  }

  async function restockItem(id: string) {
    const add = restock[id] || 0;
    if (!add || add <= 0) return toast.error("Enter a positive quantity");
    const item = items.find((i) => i.id === id);
    try {
      await adminApi.updateProduct(id, { stock_quantity: (item.stock_quantity || 0) + add });
      toast.success("Stock updated");
      setRestock((r) => ({ ...r, [id]: 0 }));
      load();
    } catch (e: any) {
      toast.error(getApiError(e, "Update failed"));
    }
  }

  const lowStock = items.filter((i) => i.stock_quantity <= i.min_stock_level);
  const totalValue = items.reduce((s, i) => s + (i.final_price || 0) * (i.stock_quantity || 0), 0);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-100 dark:bg-slate-950 flex items-center justify-center">
        <div className="w-16 h-16 rounded-xl bg-slate-200 dark:bg-slate-800 animate-pulse" />
      </div>
    );
  }

  return (
    <AdminShell title="Inventory" user={user}>
      <div className="flex flex-wrap gap-4 text-sm text-slate-500 dark:text-slate-400 mb-4">
        <span className="card !rounded-xl px-4 py-2">
          Items: <strong className="text-slate-900 dark:text-white">{items.length}</strong>
        </span>
        <span className="card !rounded-xl px-4 py-2">
          Low stock:{" "}
          <strong className={lowStock.length ? "text-rose-600" : "text-slate-900 dark:text-white"}>
            {lowStock.length}
          </strong>
        </span>
        <span className="card !rounded-xl px-4 py-2">
          Stock value: <strong className="text-slate-900 dark:text-white">{formatMoney(totalValue)}</strong>
        </span>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500 dark:text-slate-400 border-b dark:border-slate-700">
              <th className="py-3 px-4">Product</th>
              <th>SKU</th>
              <th>Price</th>
              <th>In stock</th>
              <th>Min level</th>
              <th>Reserved</th>
              <th className="pr-4">Restock</th>
            </tr>
          </thead>
          <tbody>
            {items.map((i) => (
              <tr key={i.id} className="border-b dark:border-slate-700 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-800/50">
                <td className="py-2.5 px-4">
                  <p className="font-medium text-slate-900 dark:text-white">{i.name}</p>
                  <p className="text-xs text-slate-400 dark:text-slate-500">{i.brand}</p>
                </td>
                <td className="text-slate-500 dark:text-slate-400">{i.sku}</td>
                <td className="text-slate-700 dark:text-slate-300">{formatMoney(i.final_price)}</td>
                <td className="text-slate-700 dark:text-slate-300">
                  <span className={i.stock_quantity <= i.min_stock_level ? "text-rose-600 font-semibold" : ""}>
                    {i.stock_quantity}
                  </span>
                  {i.stock_quantity <= i.min_stock_level && (
                    <span className="ml-1 text-xs bg-rose-100 dark:bg-rose-500/10 text-rose-600 dark:text-rose-400 rounded px-1.5 py-0.5">
                      low
                    </span>
                  )}
                </td>
                <td className="text-slate-600 dark:text-slate-400">{i.min_stock_level}</td>
                <td className="text-slate-600 dark:text-slate-400">{i.reserved || 0}</td>
                <td className="pr-4 py-2.5">
                  <div className="flex gap-1">
                    <input
                      type="number"
                      min={1}
                      value={restock[i.id] || ""}
                      onChange={(e) =>
                        setRestock((r) => ({ ...r, [i.id]: parseInt(e.target.value) || 0 }))
                      }
                      placeholder="+qty"
                      className="border dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 rounded-lg px-2 py-1 w-20 text-xs"
                    />
                    <button
                      onClick={() => restockItem(i.id)}
                      className="inline-flex items-center gap-1 px-3 py-1 rounded-lg bg-sky-600 text-white text-xs hover:bg-sky-700 transition"
                    >
                      <PackagePlus size={13} /> Add
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AdminShell>
  );
}