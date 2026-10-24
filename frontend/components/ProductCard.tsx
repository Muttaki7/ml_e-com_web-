import Link from "next/link";
import { formatMoney, mediaUrl } from "@/lib/api";
import { ImageOff, ShoppingCart } from "lucide-react";

export function ProductCard({ p }: { p: any }) {
  return (
    <Link
      href={`/products/${p.id}`}
      className="card group overflow-hidden hover:shadow-md hover:-translate-y-0.5 transition-all"
    >
      <div className="aspect-square bg-slate-100 dark:bg-slate-800 overflow-hidden relative flex items-center justify-center">
        {p.images?.[0] ? (
          <img
            src={mediaUrl(p.images[0])}
            alt={p.name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            loading="lazy"
          />
        ) : (
          <ImageOff size={28} className="text-slate-300 dark:text-slate-600" />
        )}
        {p.discount_percent > 0 && (
          <span className="absolute top-2 left-2 px-2 py-0.5 rounded-full bg-rose-500 text-white text-[11px] font-bold">
            -{Math.round(p.discount_percent)}%
          </span>
        )}
      </div>
      <div className="p-4">
        <h3 className="font-semibold text-sm text-slate-900 dark:text-slate-100 line-clamp-2">
          {p.name}
        </h3>
        <div className="mt-2 flex items-center justify-between">
          <div>
            <p className="text-sky-600 dark:text-sky-400 font-bold">{formatMoney(p.final_price)}</p>
            {p.discount_percent > 0 && (
              <p className="text-xs text-slate-400 line-through">{formatMoney(p.selling_price)}</p>
            )}
          </div>
          <span
            className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${
              p.stock_status === "in_stock"
                ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400"
                : p.stock_status === "low_stock"
                ? "bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400"
                : "bg-rose-100 text-rose-700 dark:bg-rose-500/10 dark:text-rose-400"
            }`}
          >
            {p.stock_status?.replace("_", " ")}
          </span>
        </div>
        <span className="mt-3 flex items-center gap-1.5 text-xs font-semibold text-sky-600 dark:text-sky-400">
          <ShoppingCart size={13} /> View details
        </span>
      </div>
    </Link>
  );
}