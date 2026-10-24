"use client";

import { useEffect, useState } from "react";
import { adminApi, formatMoney, getApiError } from "@/lib/api";
import { useAdminAuth } from "@/lib/useAdminAuth";
import { AdminShell } from "@/components/AdminShell";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import toast from "react-hot-toast";

const COLORS = ["#0284c7", "#059669", "#d97706", "#7c3aed", "#db2777", "#0891b2", "#4f46e5", "#ca8a04"];

export default function AdminBiPage() {
  const { user, loading } = useAdminAuth();
  const [bi, setBi] = useState<any>(null);
  const [byCategory, setByCategory] = useState<any[]>([]);

  useEffect(() => {
    if (!loading) {
      adminApi.bi().then((r) => setBi(r.data)).catch((e) => toast.error(getApiError(e, "Failed to load BI")));
      adminApi.profitByCategory().then((r) => setByCategory(r.data || [])).catch(() => {});
    }
  }, [loading]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-100 dark:bg-slate-950 flex items-center justify-center">
        <div className="w-16 h-16 rounded-xl bg-slate-200 dark:bg-slate-800 animate-pulse" />
      </div>
    );
  }

  return (
    <AdminShell title="Business Intelligence" user={user}>
      <div className="space-y-6">
        <p className="text-xs text-slate-500 dark:text-slate-400 -mt-2">
          {bi?.generated_at?.slice(0, 16)}
        </p>
        {bi?.insights?.length > 0 && (
          <div className="card p-5">
            <h2 className="font-semibold mb-3 text-slate-900 dark:text-white">AI Insights</h2>
            <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-400">
              {bi.insights.map((ins: string, i: number) => (
                <li key={i} className="flex gap-2">
                  <span className="text-sky-600">▸</span>
                  {ins}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="grid lg:grid-cols-2 gap-6">
          {/* Profit by category */}
          <div className="card p-5">
            <h2 className="font-semibold mb-4 text-slate-900 dark:text-white">Profit by Category</h2>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={byCategory}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" strokeOpacity={0.15} />
                  <XAxis dataKey="category" tick={{ fontSize: 10, fill: "#64748b" }} interval={0} angle={-20} textAnchor="end" />
                  <YAxis tick={{ fontSize: 10, fill: "#64748b" }} />
                  <Tooltip formatter={(v: number) => formatMoney(v)} contentStyle={{ borderRadius: 12 }} />
                  <Bar dataKey="profit" fill="#059669" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Revenue share */}
          <div className="card p-5">
            <h2 className="font-semibold mb-4 text-slate-900 dark:text-white">Revenue Share by Category</h2>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={byCategory}
                    dataKey="revenue"
                    nameKey="category"
                    innerRadius={45}
                    outerRadius={80}
                    paddingAngle={2}
                  >
                    {byCategory.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => formatMoney(v)} contentStyle={{ borderRadius: 12 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Top profitable products */}
        {bi?.top_profitable_products?.length > 0 && (
          <div className="card p-5">
            <h2 className="font-semibold mb-3 text-slate-900 dark:text-white">Top Profitable Products</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-slate-500 dark:text-slate-400 border-b dark:border-slate-700">
                    <th className="py-2">Product</th>
                    <th>Revenue</th>
                    <th>Profit</th>
                    <th>Qty sold</th>
                  </tr>
                </thead>
                <tbody>
                  {bi.top_profitable_products.map((p: any) => (
                    <tr key={p.product_id} className="border-b dark:border-slate-700 last:border-0">
                      <td className="py-2 text-slate-800 dark:text-slate-200">{p.name}</td>
                      <td className="text-slate-600 dark:text-slate-400">{formatMoney(p.revenue)}</td>
                      <td className="text-emerald-600 dark:text-emerald-400 font-medium">{formatMoney(p.profit)}</td>
                      <td className="text-slate-600 dark:text-slate-400">{p.qty_sold}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {bi?.low_stock_alerts?.length > 0 && (
          <div className="card p-5">
            <h2 className="font-semibold mb-3 text-rose-600 dark:text-rose-400">Low Stock Alerts</h2>
            <div className="space-y-2">
              {bi.low_stock_alerts.map((a: any) => (
                <div key={a.id} className="text-sm flex justify-between border-b dark:border-slate-700 last:border-0 py-1.5 text-slate-600 dark:text-slate-400">
                  <span className="text-slate-800 dark:text-slate-200">{a.name}</span>
                  <span className={a.stock <= a.min_level ? "text-rose-600 font-medium" : ""}>
                    {a.stock} / min {a.min_level}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </AdminShell>
  );
}