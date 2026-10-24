"use client";

import { useEffect, useState } from "react";
import { authApi, getApiError } from "@/lib/api";
import toast from "react-hot-toast";
import { ShieldCheck, ShieldOff, KeyRound } from "lucide-react";

type Scope = "customer" | "admin";

const STORAGE_KEY: Record<Scope, string> = {
  customer: "customer_user",
  admin: "admin_user",
};

/**
 * TOTP 2FA enrollment. Setup returns a QR + one-time backup codes; the account
 * owner confirms with a code from their authenticator app.
 *
 * Admins have no self-service disable — a Main Admin resets it via
 * /admins/{id}/2fa/reset — so the disable affordance is customer-only.
 */
export default function TwoFactorCard({ scope = "customer" }: { scope?: Scope }) {
  const [enabled, setEnabled] = useState(false);
  const [busy, setBusy] = useState(false);
  const [setup, setSetup] = useState<any>(null);
  const [confirmCode, setConfirmCode] = useState("");
  const [disableCode, setDisableCode] = useState("");
  const [showDisable, setShowDisable] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY[scope]);
      if (raw) setEnabled(!!JSON.parse(raw).two_factor_enabled);
    } catch {}
  }, [scope]);

  function persistEnabled(next: boolean) {
    setEnabled(next);
    try {
      const key = STORAGE_KEY[scope];
      const raw = localStorage.getItem(key);
      if (raw) {
        const u = JSON.parse(raw);
        u.two_factor_enabled = next;
        localStorage.setItem(key, JSON.stringify(u));
      }
    } catch {}
  }

  async function startSetup() {
    setBusy(true);
    try {
      const { data } = scope === "admin" ? await authApi.admin2faSetup() : await authApi.customer2faSetup();
      setSetup(data);
      setConfirmCode("");
    } catch (err: any) {
      toast.error(getApiError(err, "Could not start 2FA setup"));
    } finally {
      setBusy(false);
    }
  }

  async function confirmSetup(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      if (scope === "admin") await authApi.admin2faConfirm(confirmCode);
      else await authApi.customer2faConfirm(confirmCode);
      toast.success("2FA is now enabled on your account");
      setSetup(null);
      persistEnabled(true);
    } catch (err: any) {
      toast.error(getApiError(err, "Invalid code"));
    } finally {
      setBusy(false);
    }
  }

  async function disable(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await authApi.customer2faDisable(disableCode);
      toast.success("2FA disabled");
      setShowDisable(false);
      setDisableCode("");
      persistEnabled(false);
    } catch (err: any) {
      toast.error(getApiError(err, "Invalid code"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 font-semibold text-slate-900 dark:text-white">
            <ShieldCheck size={18} className="text-emerald-600" /> Two-Factor Authentication
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-lg">
            Add an extra layer of security to your account with an authenticator app
            (Google Authenticator, Authy, 1Password…). You will be asked for a code at login.
            {scope === "admin" && " Once enabled, every admin login requires a code."}
          </p>
        </div>
        {enabled ? (
          <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400">
            Enabled
          </span>
        ) : (
          <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            Not enabled
          </span>
        )}
      </div>

      {setup ? (
        <form onSubmit={confirmSetup} className="mt-4 space-y-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="shrink-0 p-2 bg-white rounded-xl border dark:border-slate-700 self-start">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`data:image/png;base64,${setup.qr_code_base64}`}
                alt="2FA QR code"
                className="w-40 h-40"
              />
            </div>
            <div className="space-y-2 text-sm min-w-0">
              <p className="text-slate-600 dark:text-slate-400">
                1. Scan the QR code with your authenticator app.
              </p>
              <p className="text-slate-600 dark:text-slate-400">
                2. Save these backup codes somewhere safe — each works once:
              </p>
              <div className="grid grid-cols-2 gap-1 font-mono text-xs bg-slate-100 dark:bg-slate-800 rounded-lg p-3">
                {(setup.backup_codes || []).map((c: string) => (
                  <span key={c}>{c}</span>
                ))}
              </div>
              <p className="text-xs text-slate-400 break-all">
                Can&apos;t scan? Enter this secret manually: {setup.secret}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <input
              value={confirmCode}
              onChange={(e) => setConfirmCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
              placeholder="6-digit code"
              className="input !w-40 text-center tracking-widest !font-mono"
              required
            />
            <button type="submit" disabled={busy || confirmCode.length !== 6} className="btn-primary !py-2">
              Verify & Enable
            </button>
            <button type="button" onClick={() => setSetup(null)} className="btn-outline !py-2">
              Cancel
            </button>
          </div>
        </form>
      ) : enabled ? (
        scope === "customer" && (
          <div className="mt-4">
            {showDisable ? (
              <form onSubmit={disable} className="flex flex-wrap items-center gap-2">
                <input
                  value={disableCode}
                  onChange={(e) => setDisableCode(e.target.value.replace(/[^0-9a-zA-Z]/g, "").toUpperCase())}
                  placeholder="Current code or backup code"
                  maxLength={8}
                  className="input !w-56 text-center tracking-widest !font-mono"
                  required
                />
                <button type="submit" disabled={busy || disableCode.length < 6} className="btn-outline !py-2">
                  Confirm Disable
                </button>
                <button type="button" onClick={() => setShowDisable(false)} className="text-sm text-slate-400">
                  Cancel
                </button>
              </form>
            ) : (
              <button onClick={() => setShowDisable(true)} className="btn-outline !py-2 inline-flex gap-2">
                <ShieldOff size={15} /> Disable 2FA
              </button>
            )}
          </div>
        )
      ) : (
        <div className="mt-4">
          <button onClick={startSetup} disabled={busy} className="btn-primary !py-2 inline-flex gap-2">
            <KeyRound size={15} /> {busy ? "Preparing..." : "Enable 2FA"}
          </button>
        </div>
      )}
    </section>
  );
}
