"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { authApi, getApiError } from "@/lib/api";
import { DemoLoginPanel } from "@/components/DemoLoginPanel";
import toast from "react-hot-toast";
import { ShieldCheck, Mail, Lock, KeyRound, LogIn, ArrowLeft } from "lucide-react";

export default function AdminLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [tempToken, setTempToken] = useState("");
  const [step, setStep] = useState<"password" | "2fa">("password");
  const [loading, setLoading] = useState(false);

  function storeSession(data: any) {
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    localStorage.setItem("token_type", "admin");
    localStorage.setItem("admin_user", JSON.stringify(data.user));
  }

  async function handlePassword(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await authApi.adminLogin({ email, password });
      if (data.requires_2fa) {
        setTempToken(data.temp_token);
        setStep("2fa");
        toast("Enter the 6-digit code from your authenticator app");
      } else {
        storeSession(data);
        toast.success("Welcome to ERP");
        router.push("/admin");
      }
    } catch (err: any) {
      toast.error(getApiError(err, "Login failed"));
    } finally {
      setLoading(false);
    }
  }

  async function handle2FA(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await authApi.admin2faVerify({ temp_token: tempToken, code });
      storeSession(data);
      toast.success("2FA verified");
      router.push("/admin");
    } catch (err: any) {
      toast.error(getApiError(err, "Invalid code"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100 dark:bg-slate-950 px-4 py-10">
      <div className="w-full max-w-md card p-8">
        <div className="w-12 h-12 mx-auto rounded-xl bg-slate-900 dark:bg-sky-600 text-white flex items-center justify-center">
          <ShieldCheck size={22} />
        </div>
        <h1 className="text-2xl font-bold text-center text-slate-900 dark:text-white mt-4">Admin ERP Login</h1>
        <p className="text-center text-slate-500 dark:text-slate-400 text-sm mt-1">
          Separate authentication · TOTP 2FA available for administrators
        </p>

        <DemoLoginPanel />

        {step === "password" ? (
          <form onSubmit={handlePassword} className="mt-8 space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1 text-slate-700 dark:text-slate-300">Email</label>
              <div className="relative">
                <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input w-full !pl-10"
                  placeholder="admin@example.com"
                  required
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-slate-700 dark:text-slate-300">Password</label>
              <div className="relative">
                <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input w-full !pl-10"
                  placeholder="Your password"
                  required
                />
              </div>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full !py-3"
            >
              <LogIn size={17} /> {loading ? "Checking..." : "Continue"}
            </button>
          </form>
        ) : (
          <form onSubmit={handle2FA} className="mt-8 space-y-4">
            <p className="text-sm text-slate-600 dark:text-slate-400 text-center">
              Enter the 6-digit code for <strong className="text-slate-900 dark:text-white">{email}</strong>
              <br />
              <span className="text-xs text-slate-400">or use an 8-character backup code</span>
            </p>
            <div className="relative">
              <KeyRound size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                maxLength={8}
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/[^0-9a-zA-Z]/g, "").toUpperCase())}
                className="input w-full !pl-10 text-center text-2xl tracking-widest !font-mono"
                placeholder="000000"
                required
              />
            </div>
            <button
              type="submit"
              disabled={loading || code.length < 6}
              className="btn-primary w-full !py-3"
            >
              {loading ? "Verifying..." : "Verify & Login"}
            </button>
            <button
              type="button"
              onClick={() => { setStep("password"); setTempToken(""); setCode(""); }}
              className="w-full inline-flex items-center justify-center gap-1 text-sm text-slate-500 dark:text-slate-400 hover:text-slate-700"
            >
              <ArrowLeft size={14} /> Back
            </button>
          </form>
        )}
      </div>
    </div>
  );
}