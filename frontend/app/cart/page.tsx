"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { orderApi, settingsApi, formatMoney, getApiError, downloadBlob } from "@/lib/api";
import { StorefrontHeader } from "@/components/StorefrontHeader";
import { Footer } from "@/components/Footer";
import IntlPhoneInput, { loadCountries, type Country } from "@/components/IntlPhoneInput";
import toast from "react-hot-toast";
import { CheckCircle2, Trash2, Minus, Plus, FileDown, ArrowRight } from "lucide-react";

interface CartItem {
  product_id: string;
  name: string;
  final_price: number;
  qty: number;
  images?: string[];
}

function getCart(): CartItem[] {
  try {
    return JSON.parse(localStorage.getItem("cart") || "[]");
  } catch {
    return [];
  }
}

export default function CartPage() {
  const [items, setItems] = useState<CartItem[]>(() => getCart());
  const [loggedIn, setLoggedIn] = useState<boolean>(
    () => typeof window !== "undefined" && !!localStorage.getItem("access_token")
  );
  const [placing, setPlacing] = useState(false);
  const [invoiceLoading, setInvoiceLoading] = useState(false);
  const [placed, setPlaced] = useState<any>(null);
  const [method, setMethod] = useState("cod");
  const [storeSettings, setStoreSettings] = useState<any>(null);
  const [countries, setCountries] = useState<Country[]>([]);

  useEffect(() => {
    settingsApi
      .public()
      .then((r) => {
        setStoreSettings(r.data);
        setMethod(
          r.data?.payments?.methods?.find((m: any) => m.enabled)?.id || "cod"
        );
      })
      .catch(() => {});
    loadCountries()
      .then((list) => setCountries(list))
      .catch(() => {});
  }, []);

  const [address, setAddress] = useState(() => {
    const base = {
      full_name: "",
      phone: "",
      country: "US",
      state: "",
      city: "",
      address_line: "",
      postal_code: "",
    };
    if (typeof window === "undefined") return base;
    const cu = localStorage.getItem("customer_user");
    if (!cu) return base;
    try {
      const u = JSON.parse(cu);
      return { ...base, full_name: u.full_name || base.full_name, phone: u.phone || base.phone };
    } catch {
      return base;
    }
  });

  // Default the shipping country to the store's country once settings load
  useEffect(() => {
    const storeCountry = storeSettings?.store?.country;
    if (storeCountry) {
      setAddress((a: any) => (a.country ? a : { ...a, country: storeCountry }));
    }
  }, [storeSettings]);

  function updateQty(i: number, delta: number) {
    const next = [...items];
    next[i].qty = Math.max(1, next[i].qty + delta);
    setItems(next);
    localStorage.setItem("cart", JSON.stringify(next));
  }

  function removeItem(i: number) {
    const next = items.filter((_, idx) => idx !== i);
    setItems(next);
    localStorage.setItem("cart", JSON.stringify(next));
  }

  const paymentMethods: { id: string; label: string }[] =
    storeSettings?.payments?.methods?.filter((m: any) => m.enabled) || [];

  const subtotal = items.reduce((s, it) => s + it.final_price * it.qty, 0);
  const delivery = subtotal === 0 ? 0 : (() => {
    const d = storeSettings?.delivery || {};
    const threshold = parseFloat(d.free_delivery_threshold) || 0;
    const freeEnabled = Boolean(d.free_delivery_enabled);
    if (freeEnabled && threshold > 0 && subtotal >= threshold) return 0;
    const storeCountry = (storeSettings?.store?.country || "").toUpperCase();
    const isLocal = (address.country || "").toUpperCase() === storeCountry;
    return isLocal
      ? parseFloat(d.local_charge) || 0
      : parseFloat(d.international_charge) || 0;
  })();
  const total = subtotal + delivery;

  async function placeOrder(e: React.FormEvent) {
    e.preventDefault();
    setPlacing(true);
    try {
      const { data } = await orderApi.checkout({
        items: items.map((it) => ({ product_id: it.product_id, quantity: it.qty })),
        shipping_address: address,
        payment_method: method,
      });
      setPlaced(data);
      localStorage.removeItem("cart");
      setItems([]);
      toast.success("Order placed!");
    } catch (err: any) {
      toast.error(getApiError(err, "Checkout failed"));
    } finally {
      setPlacing(false);
    }
  }

  async function downloadInvoice() {
    const orderId = placed?.order_id || placed?.id;
    if (!orderId) return;
    setInvoiceLoading(true);
    try {
      const r = await orderApi.myInvoice(orderId);
      downloadBlob(r, `INV-${placed.order_number || orderId}.pdf`);
    } catch (err: any) {
      toast.error(getApiError(err, "Invoice download failed"));
    } finally {
      setInvoiceLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col">
      <StorefrontHeader />

      <main className="max-w-7xl mx-auto px-4 py-8 w-full flex-1">
        {placed ? (
          <div className="card max-w-xl mx-auto p-8 text-center">
            <div className="w-16 h-16 mx-auto rounded-full bg-emerald-100 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
              <CheckCircle2 size={30} />
            </div>
            <h1 className="text-2xl font-bold mt-4 text-slate-900 dark:text-white">Order Confirmed</h1>
            <p className="mt-2 text-slate-600 dark:text-slate-400">
              Order <strong>{placed.order_number}</strong> · {formatMoney(placed.total)}
            </p>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Payment: {placed.payment_method} ({placed.payment_status})
            </p>
            <button
              onClick={downloadInvoice}
              disabled={invoiceLoading}
              className="btn-primary mt-6 mx-auto inline-flex"
            >
              <FileDown size={16} /> {invoiceLoading ? "Preparing…" : "Download Invoice (.pdf)"}
            </button>
            <div className="mt-4 flex items-center justify-center gap-4 text-sm">
              <Link href="/orders" className="text-sky-600 dark:text-sky-400 hover:underline">
                View my orders
              </Link>
              <Link
                href="/products"
                className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-xl bg-sky-600 text-white font-semibold hover:bg-sky-700 transition"
              >
                Continue Shopping <ArrowRight size={15} />
              </Link>
            </div>
          </div>
        ) : items.length === 0 ? (
          <div className="card max-w-xl mx-auto p-12 text-center">
            <h1 className="text-xl font-bold text-slate-900 dark:text-white">Your cart is empty</h1>
            <p className="mt-2 text-slate-500 text-sm">
              Browse products from sellers worldwide and add your favorites.
            </p>
            <Link href="/products" className="btn-primary inline-flex mt-6">
              Browse Products
            </Link>
          </div>
        ) : (
          <div className="grid lg:grid-cols-[1fr_380px] gap-8">
            {/* Items */}
            <div className="bg-white rounded-2xl border p-6">
              <h1 className="text-xl font-bold">Shopping Cart ({items.length})</h1>
              <div className="mt-4 space-y-3">
                {items.map((it, i) => (
                  <div key={it.product_id} className="flex items-center gap-4 border dark:border-slate-700 rounded-xl p-3 bg-white dark:bg-slate-900">
                    <div className="w-14 h-14 rounded-lg bg-slate-100 dark:bg-slate-800 overflow-hidden flex items-center justify-center text-slate-400 text-xs">
                      {it.images?.[0] ? (
                        <img src={it.images[0]} alt={it.name} className="w-full h-full object-cover" />
                      ) : (
                        it.name?.slice(0, 2)
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate text-slate-900 dark:text-white">{it.name}</p>
                      <p className="text-slate-700 dark:text-slate-300 font-semibold text-sm mt-0.5">
                        {formatMoney(it.final_price)}
                      </p>
                    </div>
                    <div className="flex items-center border rounded-lg">
                      <button
                        onClick={() => updateQty(i, -1)}
                        className="px-2.5 py-1.5 hover:bg-slate-100 dark:hover:bg-slate-800"
                      >
                      <Minus size={14} />
                    </button>
                    <span className="px-3 text-sm">{it.qty}</span>
                    <button
                      onClick={() => updateQty(i, 1)}
                      className="px-2.5 py-1.5 hover:bg-slate-100 dark:hover:bg-slate-800"
                    >
                      <Plus size={14} />
                    </button>
                  </div>
                  <button
                    onClick={() => removeItem(i)}
                    className="text-slate-400 hover:text-red-600 p-1"
                    title="Remove"
                  >
                    <Trash2 size={17} />
                  </button>
                </div>
              ))}
            </div>
          </div>

            {/* Checkout form */}
            <div className="space-y-4">
              {!loggedIn ? (
                <div className="bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/30 rounded-2xl p-4 text-sm">
                  <p className="font-medium text-amber-800 dark:text-amber-400">Sign in required to place an order.</p>
                  <Link
                    href="/login"
                    className="mt-3 inline-block w-full text-center py-2 rounded-xl bg-slate-900 dark:bg-sky-600 text-white text-sm font-medium"
                  >
                    Login / Register
                  </Link>
                </div>
              ) : (
                <form onSubmit={placeOrder} className="card p-6 space-y-4">
                  <h2 className="font-bold text-slate-900 dark:text-white">Shipping Details</h2>
                  <div className="grid grid-cols-2 gap-3">
                    <input
                      required
                      placeholder="Full name"
                      value={address.full_name}
                      onChange={(e) => setAddress({ ...address, full_name: e.target.value })}
                      className="input col-span-2"
                    />
                    <div className="col-span-2">
                      <IntlPhoneInput
                        value={address.phone}
                        onChange={(v) => setAddress({ ...address, phone: v })}
                        defaultCountry={address.country}
                      />
                    </div>
                    <select
                      required
                      value={address.country}
                      onChange={(e) => setAddress({ ...address, country: e.target.value })}
                      className="input col-span-2"
                    >
                      {countries.map((c) => (
                        <option key={c.code} value={c.code}>
                          {c.name}
                        </option>
                      ))}
                      {!countries.length && <option value={address.country}>{address.country}</option>}
                    </select>
                    <input
                      required
                      placeholder="City"
                      value={address.city}
                      onChange={(e) => setAddress({ ...address, city: e.target.value })}
                      className="input"
                    />
                    <input
                      placeholder="State / Province (optional)"
                      value={address.state}
                      onChange={(e) => setAddress({ ...address, state: e.target.value })}
                      className="input"
                    />
                    <input
                      placeholder="Postal code"
                      value={address.postal_code}
                      onChange={(e) => setAddress({ ...address, postal_code: e.target.value })}
                      className="input"
                    />
                    <textarea
                      required
                      placeholder="Street address / area"
                      value={address.address_line}
                      onChange={(e) => setAddress({ ...address, address_line: e.target.value })}
                      className="input col-span-2"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2 text-slate-900 dark:text-slate-200">Payment method</label>
                    <div className="grid grid-cols-2 gap-2">
                      {paymentMethods.map((pm) => (
                        <button
                          key={pm.id}
                          type="button"
                          onClick={() => setMethod(pm.id)}
                          className={`px-3 py-2 rounded-xl border text-xs font-medium transition ${
                            method === pm.id
                              ? "border-sky-600 bg-sky-50 dark:bg-sky-500/10 text-sky-700 dark:text-sky-400"
                              : "border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-900"
                          }`}
                        >
                          {pm.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="border-t dark:border-slate-700 pt-4 space-y-1 text-sm">
                    <div className="flex justify-between text-slate-600 dark:text-slate-400">
                      <span>Subtotal</span>
                      <span>{formatMoney(subtotal)}</span>
                    </div>
                    <div className="flex justify-between text-slate-600 dark:text-slate-400">
                      <span>Delivery</span>
                      <span>{delivery === 0 ? "Free" : formatMoney(delivery)}</span>
                    </div>
                    <div className="flex justify-between font-bold text-base mt-1">
                      <span className="text-slate-900 dark:text-white">Total</span>
                      <span className="text-sky-600 dark:text-sky-400">{formatMoney(total)}</span>
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={placing}
                    className="btn-primary w-full !py-3"
                  >
                    {placing ? "Placing order..." : `Place Order · ${formatMoney(total)}`}
                  </button>
                </form>
              )}
            </div>
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}