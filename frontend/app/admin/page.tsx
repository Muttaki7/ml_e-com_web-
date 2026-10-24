"use client";

import { useEffect, useState } from "react";
import { adminApi, formatMoney } from "@/lib/api";
import { useAdminAuth } from "@/lib/useAdminAuth";
import { AdminShell } from "@/components/AdminShell";
import { TrendingUp, TrendingDown } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

export default function AdminDashboard() {
  const { user, loading } = useAdminAuth();
  const [kpis, setKpis] = useState<any>(null);
  const [sales, setSales] = useState<any[]>([]);
  const [bi, setBi] = useState<any>(null);

  useEffect(() => {
    if (loading) return;
    Promise.all([
      adminApi.dashboard().then((r) => setKpis(r.data)).catch(() => {}),
      adminApi.salesByDay(14).then((r) => setSales(r.data)).catch(() => {}),
      adminApi.bi().then((r) => setBi(r.data)).catch(() => {}),
    ]);
  }, [loading]);

  const cards = kpis
    ? [
        { label: "Total Sales", value: formatMoney(kpis.total_sales) },
        { label: "Today", value: formatMoney(kpis.today_sales) },
        { label: "Monthly", value: formatMoney(kpis.monthly_sales) },
        { label: "Orders", value: kpis.total_orders },
        { label: "Pending", value: kpis.pending_orders },
        { label: "Customers", value: kpis.total_customers },
        { label: "Products", value: kpis.total_products },
        { label: "Low Stock", value: kpis.low_stock_products },
        { label: "Gross Profit", value: formatMoney(kpis.gross_profit) },
        { label: "Margin", value: `${kpis.profit_margin_percent}%` },
      ]
    : [];

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-100 dark:bg-slate-950 flex items-center justify-center">
        <div className="w-16 h-16 rounded-xl bg-slate-200 dark:bg-slate-800 animate-pulse" />
      </div>
    );
  }

  return (
    <AdminShell title="Dashboard" user={user}>
      <div className="space-y-6">
        {/* KPI cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {cards.map((c) => (
            <div key={c.label} className="card p-4">
              <div className="flex items-center gap-2">
                <p className="text-xs text-slate-500 dark:text-slate-400">{c.label}</p>
                {parseFloat(String(c.value).replace(/[^\d.-]/g, "") || "0") < 0 ? (
                  <TrendingDown size={13} className="text-rose-500" />
                ) : (
                  <TrendingUp size={13} className="text-emerald-500" />
                )}
              </div>
              <p className="text-lg font-bold mt-1 text-slate-900 dark:text-white">{c.value}</p>
            </div>
          ))}
        </div>

        {/* Chart */}
        <div className="card p-4">
          <h2 className="font-semibold mb-4 text-slate-900 dark:text-white">Sales (last 14 days)</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sales}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" strokeOpacity={0.15} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#64748b" }} />
                <YAxis tick={{ fontSize: 11, fill: "#64748b" }} />
                <Tooltip formatter={(v: number) => formatMoney(v)} contentStyle={{ borderRadius: 12 }} />
                <Bar dataKey="sales" fill="#0284c7" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* BI insights */}
        {bi && (
          <div className="card p-4">
            <h2 className="font-semibold mb-3 text-slate-900 dark:text-white">Business Intelligence Insights</h2>
            <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-400">
              {(bi.insights || []).map((ins: string, i: number) => (
                <li key={i} className="flex gap-2">
                  <span className="text-sky-600">▸</span>
                  {ins}
                </li>
              ))}
            </ul>
            {bi.top_profitable_products?.length > 0 && (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-slate-500 dark:text-slate-400 border-b dark:border-slate-700">
                      <th className="py-2">Product</th>
                      <th>Revenue</th>
                      <th>Profit</th>
                      <th>Qty</th>
                    </tr>
                  </thead>
                  <tbody>
                    {bi.top_profitable_products.slice(0, 5).map((p: any) => (
                      <tr key={p.product_id} className="border-b dark:border-slate-700 last:border-0">
                        <td className="py-2 text-slate-800 dark:text-slate-200">{p.name}</td>
                        <td className="text-slate-600 dark:text-slate-400">{formatMoney(p.revenue)}</td>
                        <td className="text-emerald-600 dark:text-emerald-400">{formatMoney(p.profit)}</td>
                        <td className="text-slate-600 dark:text-slate-400">{p.qty_sold}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </AdminShell>
  );
}