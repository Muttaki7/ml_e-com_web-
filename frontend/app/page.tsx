import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  Boxes,
  Check,
  Globe2,
  LayoutDashboard,
  LineChart,
  LockKeyhole,
  PackageCheck,
  PlayCircle,
  ShieldCheck,
  ShoppingBag,
  Sparkles,
  Store,
  Truck,
} from "lucide-react";

const TITLE = "GlobalShop — Global Commerce & ERP Platform";
const DESCRIPTION =
  "A complete commerce platform: storefront, ERP dashboard, orders, invoices and AI demand forecasting for 200+ countries.";

export const metadata = {
  title: TITLE,
  description: DESCRIPTION,
  openGraph: {
    title: TITLE,
    description: DESCRIPTION,
    images: [{ url: "/vibe96-cover.webp", width: 1280, height: 720 }],
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
    description: DESCRIPTION,
    images: ["/vibe96-cover.webp"],
  },
};

const FEATURES = [
  {
    icon: Store,
    title: "Global storefront",
    body: "A fast, responsive shop with slideshows, categories, search and Cash on Delivery for 200+ countries.",
  },
  {
    icon: LayoutDashboard,
    title: "Full ERP dashboard",
    body: "Orders, products, inventory, suppliers, customers, staff roles and store settings in one workspace.",
  },
  {
    icon: LineChart,
    title: "AI demand forecasting",
    body: "7, 30 and 90-day forecasts, purchase recommendations and a Product Intelligence Score for every SKU.",
  },
  {
    icon: PackageCheck,
    title: "Orders & invoices",
    body: "Atomic stock reservation, status tracking and authenticated PDF invoices generated on demand.",
  },
  {
    icon: ShieldCheck,
    title: "Secure by default",
    body: "Separate admin and customer tokens, TOTP two-factor authentication, lockouts and audit logging.",
  },
  {
    icon: Globe2,
    title: "Any country",
    body: "ISO-3166 addresses, E.164 phones, local currency and domestic or international delivery pricing.",
  },
];

const SCREENS = [
  {
    src: "/landing/admin-dashboard.webp",
    label: "ERP dashboard",
    title: "Revenue, stock and orders at a glance",
  },
  {
    src: "/landing/storefront.webp",
    label: "Storefront",
    title: "A storefront built to convert",
  },
  {
    src: "/landing/ai-forecast.webp",
    label: "AI forecasting",
    title: "Know what to reorder before you run out",
  },
];

const METRICS = [
  { value: "200+", label: "countries & territories" },
  { value: "6", label: "ERP modules in one app" },
  { value: "7/30/90", label: "day demand forecasts" },
  { value: "2FA", label: "TOTP for administrators" },
];

function BrowserFrame({ src, alt, className = "" }: { src: string; alt: string; className?: string }) {
  return (
    <div className={`overflow-hidden rounded-2xl border border-white/15 bg-slate-900 shadow-2xl shadow-black/40 ${className}`}>
      <div className="flex items-center gap-1.5 border-b border-white/10 bg-slate-950/80 px-3 py-2">
        <span className="h-2 w-2 rounded-full bg-rose-400/80" />
        <span className="h-2 w-2 rounded-full bg-amber-300/80" />
        <span className="h-2 w-2 rounded-full bg-emerald-400/80" />
        <span className="ml-2 truncate rounded-md bg-white/5 px-2 py-0.5 text-[10px] text-slate-400">
          gcart.com
        </span>
      </div>
      <img src={src} alt={alt} className="block w-full" loading="lazy" decoding="async" />
    </div>
  );
}

export default function LandingPage() {
  return (
    <main className="min-h-screen overflow-hidden bg-[#050912] text-white">
      {/* ambient background */}
      <div className="pointer-events-none fixed inset-0 -z-10">
        <div className="absolute -top-40 left-1/2 h-[520px] w-[820px] -translate-x-1/2 rounded-full bg-violet-600/25 blur-[140px]" />
        <div className="absolute -right-40 top-40 h-[420px] w-[520px] rounded-full bg-sky-500/20 blur-[120px]" />
        <div className="absolute bottom-0 left-0 h-[380px] w-[520px] rounded-full bg-indigo-700/20 blur-[120px]" />
      </div>

      <header className="sticky top-0 z-40 border-b border-white/5 bg-[#050912]/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-2 text-lg font-extrabold tracking-tight text-white">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-sky-500">
              <Store size={17} />
            </span>
            <span>
              Global<span className="text-sky-400">Shop</span>
            </span>
          </Link>
          <nav className="hidden items-center gap-7 text-sm text-slate-300 md:flex">
            <a href="#platform" className="transition hover:text-white">Platform</a>
            <a href="#screens" className="transition hover:text-white">Screenshots</a>
            <a href="#demo" className="transition hover:text-white">Demo access</a>
          </nav>
          <div className="flex items-center gap-2">
            <Link
              href="/admin/login?demo=admin"
              className="hidden rounded-xl border border-white/15 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:bg-white/5 sm:inline-flex"
            >
              Admin demo
            </Link>
            <Link
              href="/shop"
              className="inline-flex items-center gap-1.5 rounded-xl bg-white px-4 py-2 text-sm font-bold text-slate-950 transition hover:bg-sky-50"
            >
              Live Demo <ArrowRight size={15} />
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto grid max-w-7xl items-center gap-12 px-4 pb-16 pt-14 sm:px-6 md:pt-20 lg:grid-cols-[1.05fr_1fr]">
        <div className="fade-up">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-violet-400/30 bg-violet-500/10 px-3 py-1 text-xs font-semibold text-violet-200">
            <Sparkles size={13} /> Commerce + ERP + AI in one platform
          </span>
          <h1 className="mt-5 text-4xl font-extrabold leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl">
            Run a global store
            <span className="block bg-gradient-to-r from-violet-400 via-sky-400 to-cyan-300 bg-clip-text text-transparent">
              from one dashboard.
            </span>
          </h1>
          <p className="mt-5 max-w-xl text-base leading-relaxed text-slate-300 sm:text-lg">
            GlobalShop combines a modern storefront with a complete ERP: orders, inventory,
            invoices, staff permissions and AI demand forecasting — built for customers in
            200+ countries.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/shop"
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-500 to-sky-500 px-6 py-3 text-sm font-bold text-white shadow-lg shadow-violet-900/40 transition hover:from-violet-400 hover:to-sky-400"
            >
              <PlayCircle size={18} /> Live Demo
            </Link>
            <Link
              href="/admin/login?demo=admin"
              className="inline-flex items-center gap-2 rounded-xl border border-white/15 bg-white/5 px-6 py-3 text-sm font-bold text-white transition hover:bg-white/10"
            >
              <ShieldCheck size={18} /> Login as Admin
            </Link>
          </div>
          <p className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-400">
            <span className="inline-flex items-center gap-1"><Check size={13} className="text-emerald-400" /> One-click demo logins</span>
            <span className="inline-flex items-center gap-1"><Check size={13} className="text-emerald-400" /> Cash on Delivery</span>
            <span className="inline-flex items-center gap-1"><Check size={13} className="text-emerald-400" /> No real payments</span>
          </p>

          <div className="mt-10 grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
            {METRICS.map((m) => (
              <div key={m.label}>
                <p className="text-xl font-extrabold text-white">{m.value}</p>
                <p className="mt-0.5 text-[11px] leading-snug text-slate-400">{m.label}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="relative fade-up">
          <div className="absolute -inset-6 -z-10 rounded-[2rem] bg-gradient-to-br from-violet-500/25 via-sky-500/10 to-transparent blur-2xl" />
          <BrowserFrame
            src="/landing/admin-dashboard.webp"
            alt="GlobalShop ERP dashboard with revenue, orders and inventory"
            className="rotate-[-1.5deg]"
          />
          <div className="absolute -bottom-10 -right-3 w-36 overflow-hidden rounded-[1.6rem] border-[3px] border-slate-700 bg-slate-900 shadow-2xl shadow-black/60 sm:-right-5 sm:w-44">
            <img
              src="/landing/storefront-mobile.webp"
              alt="GlobalShop storefront on a phone"
              className="block h-64 w-full object-cover object-top"
              loading="lazy"
            />
            <div className="flex items-center gap-2 px-3 py-2 text-[11px] font-semibold text-slate-200">
              <ShoppingBag size={13} className="text-sky-400" /> Storefront included
            </div>
          </div>
          <div className="absolute -right-2 -top-6 rounded-xl border border-emerald-400/20 bg-emerald-950/80 px-3 py-2 text-[11px] font-semibold text-emerald-200 shadow-xl backdrop-blur sm:-right-6">
            <span className="flex items-center gap-1.5"><Sparkles size={12} /> AI forecast ready</span>
          </div>
        </div>
      </section>

      {/* Platform features */}
      <section id="platform" className="mx-auto max-w-7xl px-4 py-16 sm:px-6">
        <div className="max-w-2xl">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-sky-400">The platform</p>
          <h2 className="mt-3 text-3xl font-extrabold tracking-tight sm:text-4xl">
            Everything a growing store needs, already wired together.
          </h2>
          <p className="mt-3 text-slate-400">
            No plugins, no spreadsheets. The storefront and the back office share one catalog,
            one inventory and one order pipeline.
          </p>
        </div>

        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="group rounded-2xl border border-white/10 bg-white/[0.03] p-6 transition hover:border-sky-400/30 hover:bg-white/[0.05]"
            >
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500/25 to-sky-500/25 text-sky-300 ring-1 ring-inset ring-white/10">
                <f.icon size={19} />
              </span>
              <h3 className="mt-4 font-bold text-white">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Screenshots */}
      <section id="screens" className="mx-auto max-w-7xl px-4 py-16 sm:px-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-sky-400">Inside the product</p>
            <h2 className="mt-3 text-3xl font-extrabold tracking-tight sm:text-4xl">
              Real screens from the running app.
            </h2>
          </div>
          <Link
            href="/shop"
            className="inline-flex items-center gap-1.5 rounded-xl border border-white/15 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:bg-white/5"
          >
            Open the storefront <ArrowRight size={15} />
          </Link>
        </div>

        <div className="mt-8 grid gap-5 lg:grid-cols-3">
          {SCREENS.map((s) => (
            <figure key={s.label} className="group">
              <div className="overflow-hidden rounded-2xl border border-white/10 bg-slate-900 shadow-xl shadow-black/30 transition group-hover:border-sky-400/30">
                <img
                  src={s.src}
                  alt={s.title}
                  className="block aspect-[16/10] w-full object-cover object-top"
                  loading="lazy"
                  decoding="async"
                />
              </div>
              <figcaption className="mt-3">
                <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-sky-400">{s.label}</p>
                <p className="mt-1 text-sm font-semibold text-slate-200">{s.title}</p>
              </figcaption>
            </figure>
          ))}
        </div>
      </section>

      {/* Demo access */}
      <section id="demo" className="mx-auto max-w-7xl px-4 py-16 sm:px-6">
        <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-violet-600/20 via-slate-900/60 to-sky-600/15 p-8 sm:p-12">
          <div className="relative grid gap-10 lg:grid-cols-[1fr_1.1fr] lg:items-center">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-sky-300">Try it now</p>
              <h2 className="mt-3 text-3xl font-extrabold tracking-tight sm:text-4xl">
                Two one-click demo logins.
              </h2>
              <p className="mt-3 max-w-lg text-slate-300">
                Explore the storefront as a shopper, or open the ERP as an administrator.
                The demo runs on seeded products and demo orders only.
              </p>
              <div className="mt-6 flex flex-wrap gap-3 text-xs text-slate-400">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-white/5 px-3 py-1">
                  <LockKeyhole size={13} /> Separate admin &amp; customer sessions
                </span>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-white/5 px-3 py-1">
                  <Truck size={13} /> COD checkout
                </span>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-5">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500/15 text-sky-300">
                  <ShieldCheck size={19} />
                </span>
                <h3 className="mt-4 font-bold">Admin demo</h3>
                <p className="mt-1 text-xs leading-relaxed text-slate-400">
                  Orders, inventory, invoices, analytics and AI forecasting.
                </p>
                <Link
                  href="/admin/login?demo=admin"
                  className="mt-4 inline-flex w-full items-center justify-center gap-1.5 rounded-xl bg-sky-500 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-sky-400"
                >
                  Login as Admin <ArrowRight size={15} />
                </Link>
              </div>
              <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-5">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-violet-500/15 text-violet-300">
                  <ShoppingBag size={19} />
                </span>
                <h3 className="mt-4 font-bold">Shopper demo</h3>
                <p className="mt-1 text-xs leading-relaxed text-slate-400">
                  Browse products, add to cart and place a demo order.
                </p>
                <Link
                  href="/login?demo=customer"
                  className="mt-4 inline-flex w-full items-center justify-center gap-1.5 rounded-xl bg-violet-500 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-violet-400"
                >
                  Login as User <ArrowRight size={15} />
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-7xl px-4 pb-20 sm:px-6">
        <div className="flex flex-col items-center justify-between gap-6 rounded-3xl border border-white/10 bg-white/[0.03] px-8 py-10 text-center md:flex-row md:text-left">
          <div>
            <h2 className="text-2xl font-extrabold tracking-tight sm:text-3xl">
              Open the live storefront.
            </h2>
            <p className="mt-2 text-sm text-slate-400">
              Browse the catalog, place a Cash on Delivery order, then switch to the ERP.
            </p>
          </div>
          <div className="flex flex-wrap justify-center gap-3">
            <Link
              href="/shop"
              className="inline-flex items-center gap-2 rounded-xl bg-white px-6 py-3 text-sm font-bold text-slate-950 transition hover:bg-sky-50"
            >
              <ShoppingBag size={17} /> Live Demo
            </Link>
            <Link
              href="/admin/login?demo=admin"
              className="inline-flex items-center gap-2 rounded-xl border border-white/15 px-6 py-3 text-sm font-bold text-white transition hover:bg-white/5"
            >
              <BarChart3 size={17} /> Admin demo
            </Link>
          </div>
        </div>
      </section>

      <footer className="border-t border-white/5">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-3 px-4 py-8 text-xs text-slate-500 sm:flex-row sm:px-6">
          <div className="flex items-center gap-2 font-bold text-slate-300">
            <Boxes size={15} className="text-sky-400" /> GlobalShop
          </div>
          <p>Global commerce &amp; ERP platform · Demo data only</p>
          <div className="flex items-center gap-4">
            <Link href="/shop" className="transition hover:text-slate-300">Storefront</Link>
            <Link href="/admin/login" className="transition hover:text-slate-300">Admin</Link>
          </div>
        </div>
      </footer>
    </main>
  );
}
