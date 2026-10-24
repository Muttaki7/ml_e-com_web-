"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Package, ShoppingCart, LayoutGrid, Store, LogOut } from "lucide-react";

export function StorefrontHeader() {
  const pathname = usePathname();
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoggedIn(!!localStorage.getItem("access_token"));
  }, [pathname]);

  const linkCls = (href: string) =>
    `flex items-center gap-1.5 text-sm font-medium transition ${
      pathname === href
        ? "text-sky-600 dark:text-sky-400"
        : "text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white"
    }`;

  return (
    <header className="sticky top-0 z-40 bg-white/80 dark:bg-slate-950/80 backdrop-blur border-b border-slate-200 dark:border-slate-800">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between gap-4">
        <Link href="/" className="flex items-center gap-2 text-xl font-extrabold tracking-tight">
          <span className="w-8 h-8 rounded-lg bg-sky-600 text-white flex items-center justify-center">
            <Store size={17} />
          </span>
          <span className="text-slate-900 dark:text-white">
            Global<span className="text-sky-600 dark:text-sky-400">Shop</span>
          </span>
        </Link>

        <nav className="hidden md:flex items-center gap-5">
          <Link href="/" className={linkCls("/")}>
            <Home size={16} /> Home
          </Link>
          <Link href="/products" className={linkCls("/products")}>
            <LayoutGrid size={16} /> Products
          </Link>
          <Link href="/orders" className={linkCls("/orders")}>
            <Package size={16} /> My Orders
          </Link>
        </nav>

        <div className="flex items-center gap-2">
          <Link href="/cart" className="relative p-2.5 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 transition">
            <ShoppingCart size={19} className="text-slate-700 dark:text-slate-200" />
          </Link>
          {loggedIn ? (
            <Link
              href="/login"
              onClick={() => {
                localStorage.removeItem("access_token");
                localStorage.removeItem("refresh_token");
              }}
              className="text-slate-500 dark:text-slate-400 hover:text-red-500"
              title="Logout"
            >
              <LogOut size={19} />
            </Link>
          ) : (
            <Link href="/login" className="btn-primary !py-2">
              Sign in
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}