import Link from "next/link";
import { Store, Truck, ShieldCheck, Headset, MapPin, Mail, Phone } from "lucide-react";

const FEATURES = [
  { icon: Truck, title: "Fast Worldwide Delivery", sub: "Free over the order threshold" },
  { icon: ShieldCheck, title: "Secure Checkout", sub: "Cash on Delivery · 200+ countries" },
  { icon: Headset, title: "24/7 Support", sub: "Call or chat any time" },
];

export function Footer() {
  return (
    <footer className="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 mt-auto">
      <div className="max-w-7xl mx-auto px-4 py-12 grid gap-8 md:grid-cols-4">
        <div>
          <div className="flex items-center gap-2 font-extrabold text-lg">
            <span className="w-8 h-8 rounded-lg bg-sky-600 text-white flex items-center justify-center">
              <Store size={16} />
            </span>
            Global<span className="text-sky-600">Shop</span>
          </div>
          <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">
            A global commerce &amp; ERP platform powered by AI demand forecasting.
          </p>
        </div>
        <div>
          <h4 className="font-semibold text-slate-900 dark:text-white">Shop</h4>
          <ul className="mt-3 space-y-2 text-sm text-slate-500 dark:text-slate-400">
            <li><Link href="/products" className="hover:text-sky-600">All Products</Link></li>
            <li><Link href="/products?q=" className="hover:text-sky-600">Featured</Link></li>
            <li><Link href="/cart" className="hover:text-sky-600">Cart</Link></li>
            <li><Link href="/orders" className="hover:text-sky-600">My Orders</Link></li>
          </ul>
        </div>
        <div>
          <h4 className="font-semibold text-slate-900 dark:text-white">Get in touch</h4>
          <ul className="mt-3 space-y-2 text-sm text-slate-500 dark:text-slate-400">
            <li className="flex items-center gap-2"><MapPin size={15} /> Serving 200+ countries</li>
            <li className="flex items-center gap-2"><Mail size={15} /> tsiitsolutions1@gmail.com</li>
            <li className="flex items-center gap-2"><Phone size={15} /> +880 1747-875143</li>
          </ul>
        </div>
        <div>
          <h4 className="font-semibold text-slate-900 dark:text-white">Featured</h4>
          <ul className="mt-3 space-y-3">
            {FEATURES.map((f) => (
              <li key={f.title} className="flex items-start gap-3 text-sm">
                <f.icon size={18} className="text-sky-600 shrink-0 mt-0.5" />
                <span>
                  <span className="block font-medium text-slate-700 dark:text-slate-200">{f.title}</span>
                  <span className="text-slate-500 dark:text-slate-400 text-xs">{f.sub}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
      <div className="border-t border-slate-200 dark:border-slate-800 py-5 text-center text-xs text-slate-400 dark:text-slate-500">
        A benchmark product of TSI IT Solutions<br className="sm:hidden" />
        <span className="flex items-center justify-center gap-4 mt-1">
          <span className="inline-flex items-center gap-1">Phone: +880 1747-875143</span>
          <span className="hidden sm:inline">·</span>
          <span className="inline-flex items-center gap-1">Email: tsiitsolutions1@gmail.com</span>
        </span>
      </div>
    </footer>
  );
}