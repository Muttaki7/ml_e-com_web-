"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { productApi, settingsApi } from "@/lib/api";
import { StorefrontHeader } from "@/components/StorefrontHeader";
import { Footer } from "@/components/Footer";
import { ProductCard } from "@/components/ProductCard";
import {
  ArrowRight, Sparkles, Truck, ShieldCheck, BadgePercent, ShoppingBag, Zap,
} from "lucide-react";

const CATEGORY_GRADIENTS = [
  "from-sky-500 to-indigo-600",
  "from-emerald-500 to-teal-600",
  "from-rose-500 to-orange-500",
  "from-violet-500 to-purple-600",
  "from-amber-500 to-yellow-500",
  "from-cyan-500 to-sky-600",
];

const HERO_SLIDE_MS = 6000;
const POSTER_SLIDE_MS = 5000;

function useAutoSlideshow(images: string[], intervalMs: number) {
  const [state, setState] = useState<{ index: number; previous: number | null }>({
    index: 0,
    previous: null,
  });
  const count = images.length;
  const index = count ? state.index % count : 0;

  useEffect(() => {
    if (count <= 1) return;
    const timer = window.setTimeout(() => {
      setState((s) => {
        const current = s.index % count;
        return { index: (current + 1) % count, previous: current };
      });
    }, intervalMs);
    return () => window.clearTimeout(timer);
  }, [count, index, intervalMs]);

  useEffect(() => {
    if (count <= 1) return;
    const next = images[(index + 1) % count];
    if (!next) return;
    const preload = new window.Image();
    preload.src = next;
  }, [count, images, index]);

  function goTo(next: number) {
    if (!count) return;
    setState((s) => {
      const current = s.index % count;
      const target = ((next % count) + count) % count;
      return target === current ? s : { index: target, previous: current };
    });
  }

  return { index, previous: state.previous, goTo };
}

function SectionHead({ icon: Icon, title, href }: { icon: any; title: string; href: string }) {
  return (
    <div className="flex items-center justify-between">
      <h2 className="flex items-center gap-2 text-xl font-bold text-slate-900 dark:text-white">
        <Icon size={20} className="text-sky-600 dark:text-sky-400" /> {title}
      </h2>
      <Link
        href={href}
        className="flex items-center gap-1 text-sm font-semibold text-sky-600 dark:text-sky-400 hover:gap-2 transition-all"
      >
        View all <ArrowRight size={15} />
      </Link>
    </div>
  );
}

function Poster({
  title,
  subtitle,
  accent,
  images = [],
}: {
  title: string;
  subtitle: string;
  accent: string;
  images?: string[];
}) {
  const slides = useAutoSlideshow(images, POSTER_SLIDE_MS);
  const current = images[slides.index];
  const previous = slides.previous !== null ? images[slides.previous] : null;

  return (
    <div
      className={`relative overflow-hidden rounded-2xl aspect-[4/3] flex flex-col justify-end text-white bg-gradient-to-br ${accent} shadow-md`}
    >
      {current && (
        <div className="absolute inset-0 overflow-hidden" aria-hidden="true">
          {previous && previous !== current && (
            <img
              src={previous}
              alt=""
              loading="lazy"
              decoding="async"
              className="absolute inset-0 w-full h-full object-cover"
            />
          )}
          <img
            key={current}
            src={current}
            alt=""
            loading="lazy"
            decoding="async"
            className="absolute inset-0 w-full h-full object-cover slide-photo"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-slate-950/85 via-slate-950/25 to-transparent" />
        </div>
      )}
      <div className="relative p-5">
        <p className="text-xs font-bold uppercase tracking-widest">{title}</p>
        <p className="mt-1 font-semibold text-sm text-white/90">{subtitle}</p>
      </div>
      {images.length > 1 && (
        <div className="absolute top-3 right-3 flex items-center gap-1">
          {images.map((_, i) => (
            <button
              key={i}
              type="button"
              onClick={() => slides.goTo(i)}
              aria-label={`Show ${title || "poster"} photo ${i + 1}`}
              aria-current={i === slides.index}
              className={`h-1.5 rounded-full transition-all ${
                i === slides.index ? "w-5 bg-white" : "w-1.5 bg-white/55 hover:bg-white/90"
              }`}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function HomePage() {
  const [featured, setFeatured] = useState<any[]>([]);
  const [newest, setNewest] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [banner, setBanner] = useState<any>(null);
  const [posters, setPosters] = useState<any[]>([]);

  const bannerImages: string[] = Array.isArray(banner?.images)
    ? banner.images.filter((src: any) => typeof src === "string" && src.length > 0)
    : [];
  const heroSlides = useAutoSlideshow(bannerImages, HERO_SLIDE_MS);

  useEffect(() => {
    settingsApi
      .public()
      .then((r) => {
        const d = r.data || {};
        setBanner(d.banner || null);
        setPosters((d.posters || []).filter((p: any) => p.visible).slice(0, 4));
      })
      .catch(() => {});
    productApi
      .list({ limit: 8, featured: true })
      .then((r) => setFeatured(Array.isArray(r.data) ? r.data : []))
      .catch(() => {})
      .finally(() => setLoading(false));
    productApi.list({ limit: 8 }).then((r) => setNewest(Array.isArray(r.data) ? r.data : [])).catch(() => {});
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col">
      <StorefrontHeader />

      <section className="relative overflow-hidden bg-gradient-to-br from-sky-700 via-sky-600 to-indigo-700 text-white">
        {bannerImages.length > 0 && (
          <>
            <div className="absolute inset-0 overflow-hidden" aria-hidden="true">
              {heroSlides.previous !== null && bannerImages[heroSlides.previous] && (
                <img
                  src={bannerImages[heroSlides.previous]}
                  alt=""
                  className="absolute inset-0 w-full h-full object-cover"
                />
              )}
              <img
                key={bannerImages[heroSlides.index]}
                src={bannerImages[heroSlides.index]}
                alt=""
                className="absolute inset-0 w-full h-full object-cover slide-photo"
              />
            </div>
            <div
              className="absolute inset-0 bg-gradient-to-r from-slate-950/90 via-sky-950/75 to-slate-950/40"
              aria-hidden
            />
          </>
        )}
        <div
          className="absolute inset-0 opacity-15"
          style={{
            backgroundImage:
              "radial-gradient(circle at 20% 30%, rgba(255,255,255,.25), transparent 40%), radial-gradient(circle at 80% 70%, rgba(255,255,255,.18), transparent 40%)",
          }}
          aria-hidden
        />
        <div className="relative max-w-7xl mx-auto px-4 py-16 md:py-24 grid md:grid-cols-2 gap-10 items-center">
          <div className="fade-up">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/15 text-xs font-semibold">
              <Sparkles size={13} /> {banner?.badge || "AI-powered pricing & stock forecasting"}
            </span>
            <h1 className="mt-5 text-4xl md:text-5xl font-extrabold leading-tight">
              {banner?.title || "Shop smarter, anywhere in the world"}
            </h1>
            <p className="mt-4 text-sky-100 text-lg">
              {banner?.subtitle ||
                "Products from trusted sellers. Cards, PayPal & Cash on Delivery — delivered to 200+ countries."}
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/products" className="btn bg-white text-sky-700 hover:bg-sky-50 font-bold !px-6 !py-3">
                <ShoppingBag size={18} /> Shop Now
              </Link>
              <Link
                href="/admin/login"
                className="btn border border-white/40 text-white hover:bg-white/10 !px-6 !py-3"
              >
                Open ERP Dashboard
              </Link>
            </div>
            {bannerImages.length > 1 && (
              <div className="mt-6 flex items-center gap-2" aria-label="Homepage poster slides">
                {bannerImages.map((_, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => heroSlides.goTo(i)}
                    aria-label={`Show homepage poster ${i + 1}`}
                    aria-current={i === heroSlides.index}
                    className={`h-1.5 rounded-full transition-all duration-300 ${
                      i === heroSlides.index ? "w-8 bg-white" : "w-2.5 bg-white/50 hover:bg-white/80"
                    }`}
                  />
                ))}
              </div>
            )}
          </div>
          <div className="hidden md:grid grid-cols-2 gap-4 fade-up">
            {posters.length > 0
              ? posters.map((p, i) => (
                  <Poster
                    key={i}
                    title={p.title}
                    subtitle={p.subtitle}
                    accent={p.accent || CATEGORY_GRADIENTS[i % CATEGORY_GRADIENTS.length]}
                    images={Array.isArray(p.images) ? p.images : []}
                  />
                ))
              : [
                  { title: "Big Sale", subtitle: "Up to 50% off electronics", accent: "from-rose-500 to-orange-400" },
                  { title: "Best Price", subtitle: "Everyday low prices", accent: "from-emerald-500 to-teal-400" },
                  { title: "Free Delivery", subtitle: "On orders above the threshold", accent: "from-sky-500 to-cyan-400" },
                  { title: "New Arrivals", subtitle: "Fresh collection every week", accent: "from-indigo-500 to-violet-400" },
                ].map((p, i) => (
                  <Poster key={i} title={p.title} subtitle={p.subtitle} accent={p.accent} />
                ))}
          </div>
        </div>
      </section>

      <section className="border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
        <div className="max-w-7xl mx-auto px-4 py-4 grid sm:grid-cols-3 gap-3 text-sm">
          {[
            { icon: Truck, t: "Worldwide delivery", s: "200+ countries & territories" },
            { icon: ShieldCheck, t: "100% secure", s: "Cards, PayPal, COD & more" },
            { icon: BadgePercent, t: "Smart deals", s: "AI-driven discounts" },
          ].map((x) => (
            <div key={x.t} className="flex items-center gap-3 text-slate-700 dark:text-slate-200">
              <x.icon size={22} className="text-sky-600 shrink-0" />
              <span>
                <span className="block font-semibold">{x.t}</span>
                <span className="text-xs text-slate-500 dark:text-slate-400">{x.s}</span>
              </span>
            </div>
          ))}
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-4 py-10 w-full">
        <SectionHead icon={Sparkles} title="Featured products" href="/products" />
        {loading ? (
          <div className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-80 rounded-2xl bg-slate-200 dark:bg-slate-800 animate-pulse" />
            ))}
          </div>
        ) : featured.length ? (
          <div className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-4">
            {featured.map((p) => (
              <ProductCard key={p.id} p={p} />
            ))}
          </div>
        ) : (
          <p className="mt-6 text-slate-500 dark:text-slate-400 text-sm">Featured products will appear here soon.</p>
        )}
      </section>

      <section className="max-w-7xl mx-auto px-4 pb-10 w-full">
        <SectionHead icon={Zap} title="Just arrived" href="/products" />
        <div className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-4">
          {newest.slice(0, 8).map((p) => (
            <ProductCard key={p.id} p={p} />
          ))}
        </div>
      </section>

      <Footer />
    </div>
  );
}