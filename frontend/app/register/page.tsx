"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authApi, getApiError } from "@/lib/api";
import IntlPhoneInput from "@/components/IntlPhoneInput";
import toast from "react-hot-toast";
import { Store, User, Mail, Lock, ArrowRight } from "lucide-react";

export default function CustomerRegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({ full_name: "", email: "", phone: "", password: "" });
  const [loading, setLoading] = useState(false);

  function update(key: string, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await authApi.customerRegister(form);
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      localStorage.setItem("token_type", "customer");
      localStorage.setItem("customer_user", JSON.stringify(data.user));
      toast.success("Account created. Welcome!");
      router.push("/shop");
    } catch (err: any) {
      toast.error(getApiError(err, "Registration failed"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 px-4 py-10">
      <div className="w-full max-w-md card p-8">
        <div className="w-12 h-12 mx-auto rounded-xl bg-sky-600 text-white flex items-center justify-center">
          <Store size={22} />
        </div>
        <h1 className="text-2xl font-bold text-center text-slate-900 dark:text-white mt-4">Create Account</h1>
        <p className="text-center text-slate-500 dark:text-slate-400 text-sm mt-1">
          Join GlobalShop for faster checkout &amp; order tracking
        </p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1 text-slate-700 dark:text-slate-300">Full name</label>
            <div className="relative">
              <User size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={form.full_name}
                onChange={(e) => update("full_name", e.target.value)}
                className="input w-full !pl-10"
                placeholder="Your full name"
                required
                minLength={2}
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1 text-slate-700 dark:text-slate-300">Email</label>
            <div className="relative">
              <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="email"
                value={form.email}
                onChange={(e) => update("email", e.target.value)}
                className="input w-full !pl-10"
                placeholder="you@example.com"
                required
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1 text-slate-700 dark:text-slate-300">Phone (with country code)</label>
            <IntlPhoneInput value={form.phone} onChange={(v) => update("phone", v)} />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1 text-slate-700 dark:text-slate-300">Password (min 8 chars)</label>
            <div className="relative">
              <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="password"
                value={form.password}
                onChange={(e) => update("password", e.target.value)}
                className="input w-full !pl-10"
                placeholder="Create a password"
                required
                minLength={8}
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full !py-3"
          >
            {loading ? "Creating..." : "Create Account"} <ArrowRight size={17} />
          </button>
        </form>

        <div className="mt-4 text-center text-sm">
          <Link href="/login" className="text-sky-600 dark:text-sky-400 hover:underline">
            Already have an account? Sign in
          </Link>
        </div>
        <Link href="/shop" className="block mt-4 text-center text-xs text-slate-400 hover:underline">
          Back to shop
        </Link>
      </div>
    </div>
  );
}