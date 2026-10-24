"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { getStoreSettings } from "@/lib/api";
import {
  LayoutDashboard,
  ShoppingCart,
  Package,
  Boxes,
  BrainCircuit,
  BarChart3,
  ShieldCheck,
  Settings,
  LogOut,
} from "lucide-react";

const NAV = [
  { label: "Dashboard", href: "/admin", icon: LayoutDashboard },
  { label: "Orders", href: "/admin/orders", icon: ShoppingCart },
  { label: "Products", href: "/admin/products", icon: Package },
  { label: "Inventory", href: "/admin/inventory", icon: Boxes },
  { label: "ML & Forecasts", href: "/admin/ml", icon: BrainCircuit },
  { label: "Business Intelligence", href: "/admin/bi", icon: BarChart3 },
  { label: "Administrators", href: "/admin/admins", icon: ShieldCheck },
  { label: "Settings", href: "/admin/settings", icon: Settings },
];

export function AdminShell({
  title,
  user,
  children,
}: {
  title: string;
  user: any;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [storeMeta, setStoreMeta] = useState<{ timezone?: string; currency?: string }>({});

  useEffect(() => {
    getStoreSettings()
      .then((s) => setStoreMeta(s?.store || {}))
      .catch(() => {});
  }, []);

  function logout() {
    localStorage.clear();
    router.push("/admin/login");
  }

  return (
    <div className="min-h-screen bg-slate-100 dark:bg-slate-950 flex">
      <aside className="w-64 bg-slate-900 dark:bg-slate-900 text-slate-200 hidden md:flex flex-col shrink-0">
        <div className="p-5 font-bold text-lg border-b border-slate-700 flex items-center gap-2">
          <span className="w-7 h-7 rounded-lg bg-sky-600 flex items-center justify-center text-sm text-white">
            G
          </span>
          Global ERP
        </div>
        <nav className="flex-1 p-3 space-y-1 text-sm">
          {NAV.map(({ label, href, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-2.5 px-3 py-2 rounded-lg transition ${
                pathname === href
                  ? "bg-sky-600 text-white"
                  : "hover:bg-slate-800 text-slate-300"
              }`}
            >
              <Icon size={17} />
              {label}
            </Link>
          ))}
        </nav>
        <div className="p-4 border-t border-slate-700 text-xs">
          <p className="font-medium text-slate-100">{user?.full_name || "Admin"}</p>
          <p className="text-slate-400">{user?.role}</p>
          <button
            onClick={logout}
            className="mt-2 inline-flex items-center gap-1.5 text-red-400 hover:text-red-300"
          >
            <LogOut size={13} /> Logout
          </button>
        </div>
      </aside>

      <div className="flex-1 min-w-0 flex flex-col">
        <header className="bg-white dark:bg-slate-900 border-b dark:border-slate-800 px-6 h-14 flex items-center justify-between sticky top-0 z-30">
          <h1 className="font-semibold text-slate-900 dark:text-white">{title}</h1>
          <div className="flex items-center gap-4">
            <nav className="md:hidden flex gap-1 overflow-x-auto text-xs">
              {NAV.map(({ label, href }) => (
                <Link
                  key={href}
                  href={href}
                  className={`px-2 py-1 rounded-md whitespace-nowrap ${
                    pathname === href
                      ? "bg-sky-600 text-white"
                      : "text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                  }`}
                >
                  {label}
                </Link>
              ))}
            </nav>
            <span className="text-xs text-slate-500 dark:text-slate-400 hidden sm:inline">
              {storeMeta.timezone || "UTC"} · {storeMeta.currency || "USD"}
            </span>
          </div>
        </header>

        <main className="flex-1 p-6 overflow-auto">{children}</main>
      </div>
    </div>
  );
}