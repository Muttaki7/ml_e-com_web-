"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { productApi, formatMoney } from "@/lib/api";
import { StorefrontHeader } from "@/components/StorefrontHeader";
import { Footer } from "@/components/Footer";
import toast from "react-hot-toast";
import { Minus, Plus, ShoppingCart, Zap, ArrowLeft, Truck, ShieldCheck, RotateCcw } from "lucide-react";

interface CartItem {
  product_id: string;
  name: string;
  final_price: number;
  qty: number;
}

function getCart(): CartItem[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem("cart") || "[]");
  } catch {
    return [];
  }
}

export default function ProductDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [product, setProduct] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [qty, setQty] = useState(1);
  const [activeImage, setActiveImage] = useState(0);

  useEffect(() => {
    if (!params.id) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    productApi
      .get(params.id)
      .then((r) => {
        setProduct(r.data);
        setActiveImage(0);
        setQty(1);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [params.id]);

  function addToCart() {
    if (!product) return;
    const cart = getCart();
    const existing = cart.find((i) => i.product_id === product.id);
    if (existing) {
      existing.qty += qty;
    } else {
      cart.push({
        product_id: product.id,
        name: product.name,
        final_price: product.final_price,
        qty,
      });
    }
    localStorage.setItem("cart", JSON.stringify(cart));
    toast.success("Added to cart");
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex items-center justify-center">
        <div className="w-16 h-16 rounded-xl bg-slate-200 dark:bg-slate-800 animate-pulse" />
      </div>
    );
  }

  if (!product) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col items-center justify-center gap-3">
        <p className="text-slate-500 dark:text-slate-400">Product not found.</p>
        <Link href="/products" className="text-sky-600 dark:text-sky-400 hover:underline text-sm">
          Browse products
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col">
      <StorefrontHeader />

      <main className="max-w-7xl mx-auto px-4 py-10 w-full flex-1">
        <Link href="/products" className="inline-flex items-center gap-1.5 text-sm text-slate-500 dark:text-slate-400 hover:text-sky-600 transition">
          <ArrowLeft size={15} /> Back to products
        </Link>

        <div className="mt-6 grid md:grid-cols-2 gap-10">
          <div className="card p-3">
            <div className="aspect-square bg-slate-100 dark:bg-slate-800 rounded-xl overflow-hidden flex items-center justify-center text-6xl text-slate-300">
              {product.images?.[activeImage] ? (
                <img
                  src={product.images[activeImage]}
                  alt={product.name}
                  className="w-full h-full object-cover"
                />
              ) : (
                product.name?.slice(0, 1)
              )}
            </div>
            {Array.isArray(product.images) && product.images.length > 1 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {product.images.map((url: string, i: number) => (
                  <button
                    key={url}
                    onClick={() => setActiveImage(i)}
                    className={`w-16 h-16 rounded-lg overflow-hidden border-2 ${
                      activeImage === i ? "border-sky-600" : "border-transparent"
                    }`}
                    title={`Image ${i + 1}`}
                  >
                    <img src={url} alt={`${product.name} ${i + 1}`} className="w-full h-full object-cover" />
                  </button>
                ))}
              </div>
            )}
          </div>

          <div>
            <p className="text-xs text-sky-600 dark:text-sky-400 font-medium uppercase tracking-wide">
              {product.brand || "GlobalShop"}
            </p>
            <h1 className="text-3xl font-bold mt-1 text-slate-900 dark:text-white">{product.name}</h1>
            {product.description && (
              <p className="text-slate-600 dark:text-slate-400 mt-3 text-sm">{product.description}</p>
            )}

            <div className="mt-4 flex items-end gap-3">
              <p className="text-3xl font-bold text-sky-600 dark:text-sky-400">{formatMoney(product.final_price)}</p>
              {product.discount_percent > 0 && (
                <p className="text-lg text-slate-400 line-through">
                  {formatMoney(product.selling_price)}
                </p>
              )}
            </div>
            {product.discount_percent > 0 && (
              <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-1">
                {product.discount_percent}% off today
              </p>
            )}

            <div className="mt-2">
              <span
                className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${
                  product.stock_status === "in_stock"
                    ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400"
                    : product.stock_status === "low_stock"
                    ? "bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400"
                    : "bg-rose-100 text-rose-700 dark:bg-rose-500/10 dark:text-rose-400"
                }`}
              >
                {product.stock_status?.replace("_", " ")}
              </span>
            </div>

            <div className="mt-6 flex items-center gap-4">
              <div className="flex items-center border dark:border-slate-700 rounded-xl overflow-hidden">
                <button
                  onClick={() => setQty((q) => Math.max(1, q - 1))}
                  className="px-3 py-2 text-lg hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                  <Minus size={16} />
                </button>
                <span className="px-4 py-2 text-sm font-medium min-w-[3rem] text-center text-slate-900 dark:text-white">
                  {qty}
                </span>
                <button
                  onClick={() => setQty((q) => q + 1)}
                  className="px-3 py-2 text-lg hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                  <Plus size={16} />
                </button>
              </div>
              <button
                onClick={addToCart}
                disabled={product.stock_status === "out_of_stock"}
                className="btn-primary flex-1 !py-3"
              >
                <ShoppingCart size={17} /> Add to Cart
              </button>
            </div>
            <button
              onClick={() => {
                addToCart();
                router.push("/cart");
              }}
              disabled={product.stock_status === "out_of_stock"}
              className="btn-outline mt-3 w-full !py-3 !border-sky-600 !text-sky-600"
            >
              <Zap size={17} /> Buy Now
            </button>

            <div className="mt-6 grid grid-cols-3 gap-2 text-center">
              {[
                { icon: Truck, t: "Fast delivery", s: "2–5 days" },
                { icon: ShieldCheck, t: "Secure", s: "Cards, PayPal & COD" },
                { icon: RotateCcw, t: "Easy returns", s: "7 days" },
              ].map((x) => (
                <div key={x.t} className="p-3 rounded-xl bg-slate-100 dark:bg-slate-800/70">
                  <x.icon size={18} className="mx-auto text-sky-600 dark:text-sky-400" />
                  <p className="mt-1.5 text-xs font-semibold text-slate-800 dark:text-slate-200">{x.t}</p>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400">{x.s}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}