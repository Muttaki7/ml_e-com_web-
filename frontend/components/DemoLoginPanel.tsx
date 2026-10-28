"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, ShieldCheck, ShoppingBag } from "lucide-react";
import toast from "react-hot-toast";
import { authApi, demoApi, getApiError } from "@/lib/api";

type Account = { email: string; password: string };
type DemoAccounts = { enabled: boolean; admin: Account; customer: Account };
type Kind = "admin" | "customer";

/**
 * One-click demo logins. Renders nothing unless the backend reports
 * DEMO_MODE=true, so a real store never shows or ships demo credentials.
 * `/admin/login?demo=admin` and `/login?demo=customer` sign in automatically.
 */
export function DemoLoginPanel() {
  const router = useRouter();
  const [accounts, setAccounts] = useState<DemoAccounts | null>(null);
  const [busy, setBusy] = useState<Kind | null>(null);
  const started = useRef(false);

  async function loginAs(kind: Kind, source: DemoAccounts) {
    setBusy(kind);
    try {
      if (kind === "admin") {
        const { data } = await authApi.adminLogin(source.admin);
        if (data.requires_2fa) throw new Error("Demo admin has 2FA enabled; use the form below.");
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        localStorage.setItem("token_type", "admin");
        localStorage.setItem("admin_user", JSON.stringify(data.user));
        toast.success("Signed in as the demo admin");
        router.push("/admin");
      } else {
        const { data } = await authApi.customerLogin(source.customer);
        if (data.requires_2fa) throw new Error("Demo user has 2FA enabled; use the form below.");
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        localStorage.setItem("token_type", "customer");
        localStorage.setItem("customer_user", JSON.stringify(data.user));
        toast.success("Signed in as the demo user");
        router.push("/cart");
      }
    } catch (err: any) {
      toast.error(getApiError(err, "Demo login failed"));
    } finally {
      setBusy(null);
    }
  }

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    demoApi
      .accounts()
      .then(({ data }) => {
        if (!data?.enabled) return;
        setAccounts(data);
        const params = new URLSearchParams(window.location.search);
        const requested = params.get("demo");
        if (requested === "admin" || requested === "customer") {
          params.delete("demo");
          const qs = params.toString();
          window.history.replaceState({}, "", window.location.pathname + (qs ? `?${qs}` : ""));
          loginAs(requested, data);
        }
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!accounts?.enabled) return null;

  return (
    <>
      <div className="mt-6 rounded-2xl border border-sky-200 bg-sky-50/80 p-4 dark:border-sky-900 dark:bg-sky-950/40">
        <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-sky-700 dark:text-sky-300">
          One-click demo access
        </p>
        <div className="mt-3 grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => loginAs("admin", accounts)}
            disabled={busy !== null}
            className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-slate-900 px-3 py-2.5 text-xs font-semibold text-white transition hover:bg-slate-800 disabled:opacity-60 dark:bg-sky-600 dark:hover:bg-sky-500"
          >
            {busy === "admin" ? <Loader2 size={14} className="animate-spin" /> : <ShieldCheck size={14} />}
            Login as Admin
          </button>
          <button
            type="button"
            onClick={() => loginAs("customer", accounts)}
            disabled={busy !== null}
            className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-sky-600 px-3 py-2.5 text-xs font-semibold text-white transition hover:bg-sky-500 disabled:opacity-60"
          >
            {busy === "customer" ? <Loader2 size={14} className="animate-spin" /> : <ShoppingBag size={14} />}
            Login as User
          </button>
        </div>
        <p className="mt-2 text-center text-[11px] text-sky-800/70 dark:text-sky-300/70">
          Demo data only — Cash on Delivery, no real payments.
        </p>
      </div>
      <div className="mt-6 flex items-center gap-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
        <span className="h-px flex-1 bg-slate-200 dark:bg-slate-800" />
        or sign in manually
        <span className="h-px flex-1 bg-slate-200 dark:bg-slate-800" />
      </div>
    </>
  );
}
