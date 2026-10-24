"use client";

import { useEffect, useState } from "react";
import { adminApi, formatMoney, getApiError, getStoreSettings } from "@/lib/api";
import { useAdminAuth } from "@/lib/useAdminAuth";
import { AdminShell } from "@/components/AdminShell";
import { loadCountries, type Country } from "@/components/IntlPhoneInput";
import TwoFactorCard from "@/components/TwoFactorCard";
import toast from "react-hot-toast";
import {
  Megaphone, ImageIcon, Truck, Save, Globe2, CreditCard, Building2, Upload, X, Loader2,
} from "lucide-react";

const MAX_SLIDESHOW_IMAGES = 12;

const ACCENTS = [
  "from-rose-500 to-orange-400",
  "from-emerald-500 to-teal-400",
  "from-sky-500 to-cyan-400",
  "from-indigo-500 to-violet-400",
  "from-amber-500 to-yellow-400",
  "from-fuchsia-500 to-pink-400",
  "from-slate-700 to-slate-900",
];

const COMMON_CURRENCIES = [
  { code: "USD", symbol: "$" },
  { code: "EUR", symbol: "€" },
  { code: "GBP", symbol: "£" },
  { code: "JPY", symbol: "¥" },
  { code: "AUD", symbol: "A$" },
  { code: "CAD", symbol: "C$" },
  { code: "CHF", symbol: "CHF" },
  { code: "CNY", symbol: "¥" },
  { code: "INR", symbol: "₹" },
  { code: "BDT", symbol: "৳" },
  { code: "PKR", symbol: "₨" },
  { code: "SGD", symbol: "S$" },
  { code: "AED", symbol: "د.إ" },
  { code: "SAR", symbol: "﷼" },
  { code: "BRL", symbol: "R$" },
  { code: "MXN", symbol: "$" },
  { code: "ZAR", symbol: "R" },
  { code: "NGN", symbol: "₦" },
  { code: "KES", symbol: "KSh" },
];

function ImageSlideshowEditor({
  images,
  onAdd,
  onRemove,
  max = MAX_SLIDESHOW_IMAGES,
}: {
  images: string[];
  onAdd: (urls: string[]) => void;
  onRemove: (url: string) => void;
  max?: number;
}) {
  const [uploading, setUploading] = useState(false);

  async function handleFiles(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files || []);
    e.target.value = "";
    if (!files.length) return;

    const remaining = max - images.length;
    if (remaining <= 0) {
      toast.error(`Up to ${max} photos per slideshow`);
      return;
    }
    const selected = files.slice(0, remaining);
    if (files.length > remaining) {
      toast.error(`Only ${remaining} more photo${remaining === 1 ? "" : "s"} can be added`);
    }

    setUploading(true);
    const urls: string[] = [];
    for (const file of selected) {
      if (file.size > 5 * 1024 * 1024) {
        toast.error(`${file.name} is larger than 5 MB`);
        continue;
      }
      try {
        const r = await adminApi.uploadSettingsImage(file);
        if (typeof r.data?.url === "string") urls.push(r.data.url);
      } catch (err: any) {
        toast.error(getApiError(err, `Failed to upload ${file.name}`));
      }
    }
    if (urls.length) onAdd(urls);
    setUploading(false);
  }

  const full = images.length >= max;

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {images.map((url, i) => (
          <div
            key={url}
            className="relative w-28 h-20 rounded-lg overflow-hidden border dark:border-slate-700 bg-slate-100 dark:bg-slate-800 group"
          >
            <img src={url} alt={`Slideshow photo ${i + 1}`} className="w-full h-full object-cover" />
            <span className="absolute left-1 top-1 rounded bg-black/65 px-1.5 py-0.5 text-[10px] font-semibold text-white">
              {i === 0 ? "Cover" : i + 1}
            </span>
            <button
              type="button"
              onClick={() => onRemove(url)}
              className="absolute -top-1.5 -right-1.5 w-6 h-6 rounded-full bg-rose-600 text-white flex items-center justify-center shadow"
              title="Remove photo"
              aria-label="Remove photo"
            >
              <X size={13} />
            </button>
          </div>
        ))}
        <label
          className={`w-28 h-20 rounded-lg border-2 border-dashed flex flex-col items-center justify-center gap-1 text-slate-500 dark:text-slate-400 hover:border-sky-400 hover:text-sky-600 dark:border-slate-700 cursor-pointer text-[11px] font-medium ${
            uploading || full ? "opacity-50 pointer-events-none" : ""
          }`}
        >
          {uploading ? <Loader2 size={18} className="animate-spin" /> : <Upload size={17} />}
          {uploading ? "Uploading…" : full ? "Limit reached" : "Add photos"}
          <input
            type="file"
            multiple
            accept="image/jpeg,image/png,image/webp,image/gif"
            className="hidden"
            onChange={handleFiles}
          />
        </label>
      </div>
      <p className="mt-1.5 text-[11px] text-slate-500 dark:text-slate-400">
        {images.length}/{max} photos · JPEG, PNG, WEBP or GIF · max 5 MB each
      </p>
    </div>
  );
}

export default function AdminSettingsPage() {
  const { user, loading } = useAdminAuth();
  const [saving, setSaving] = useState(false);
  const [countries, setCountries] = useState<Country[]>([]);
  const [store, setStore] = useState({
    country: "US",
    currency: "USD",
    currency_symbol: "$",
    timezone: "UTC",
  });
  const [company, setCompany] = useState({
    name: "",
    address: "",
    support_email: "",
    support_phone: "",
  });
  const [banner, setBanner] = useState({
    badge: "",
    title: "",
    subtitle: "",
    images: [] as string[],
  });
  const [posters, setPosters] = useState<any[]>([]);
  const [delivery, setDelivery] = useState({
    local_charge: 0,
    international_charge: 0,
    free_delivery_enabled: false,
    free_delivery_threshold: 0,
  });
  const [paymentMethods, setPaymentMethods] = useState<any[]>([]);

  useEffect(() => {
    loadCountries()
      .then((list) => setCountries(list))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (loading) return;
    getStoreSettings(true).catch(() => {});
    adminApi
      .settings()
      .then((r) => {
        const d = r.data || {};
        setStore({
          country: d.store?.country ?? "US",
          currency: d.store?.currency ?? "USD",
          currency_symbol: d.store?.currency_symbol ?? "$",
          timezone: d.store?.timezone ?? "UTC",
        });
        setCompany({
          name: d.company?.name ?? "",
          address: d.company?.address ?? "",
          support_email: d.company?.support_email ?? "",
          support_phone: d.company?.support_phone ?? "",
        });
        setBanner({
          badge: d.banner?.badge ?? "",
          title: d.banner?.title ?? "",
          subtitle: d.banner?.subtitle ?? "",
          images: Array.isArray(d.banner?.images) ? d.banner.images : [],
        });
        setPosters(
          (d.posters || []).map((p: any) => ({
            title: p.title ?? "",
            subtitle: p.subtitle ?? "",
            accent: p.accent ?? ACCENTS[0],
            visible: p.visible ?? true,
            images: Array.isArray(p.images) ? p.images : [],
          }))
        );
        setDelivery({
          local_charge: d.delivery?.local_charge ?? 0,
          international_charge: d.delivery?.international_charge ?? 0,
          free_delivery_enabled: d.delivery?.free_delivery_enabled ?? false,
          free_delivery_threshold: d.delivery?.free_delivery_threshold ?? 0,
        });
        setPaymentMethods(d.payments?.methods || []);
      })
      .catch(() => toast.error("Failed to load settings"));
  }, [loading]);

  function updatePoster(i: number, patch: Partial<any>) {
    setPosters((ps) => ps.map((p, idx) => (idx === i ? { ...p, ...patch } : p)));
  }

  function addPosterImages(i: number, urls: string[]) {
    setPosters((ps) =>
      ps.map((p, idx) =>
        idx === i ? { ...p, images: [...(p.images || []), ...urls] } : p
      )
    );
  }

  function removePosterImage(i: number, url: string) {
    setPosters((ps) =>
      ps.map((p, idx) =>
        idx === i ? { ...p, images: (p.images || []).filter((u: string) => u !== url) } : p
      )
    );
  }

  function addBannerImages(urls: string[]) {
    setBanner((b) => ({ ...b, images: [...b.images, ...urls] }));
  }

  function removeBannerImage(url: string) {
    setBanner((b) => ({ ...b, images: b.images.filter((u) => u !== url) }));
  }

  function updatePaymentMethod(id: string, enabled: boolean) {
    setPaymentMethods((ms) => ms.map((m) => (m.id === id ? { ...m, enabled } : m)));
  }

  function handleCountryChange(code: string) {
    const country = countries.find((c) => c.code === code);
    setStore((s) => ({
      ...s,
      country: code,
      currency: country?.currency || s.currency,
      currency_symbol: country?.currency_symbol || s.currency_symbol,
    }));
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await adminApi.updateSettings({
        store,
        company,
        banner,
        posters,
        delivery: {
          local_charge: parseFloat(delivery.local_charge as any) || 0,
          international_charge: parseFloat(delivery.international_charge as any) || 0,
          free_delivery_enabled: delivery.free_delivery_enabled,
          free_delivery_threshold: parseFloat(delivery.free_delivery_threshold as any) || 0,
        },
        payments: { methods: paymentMethods },
      });
      toast.success("Settings saved");
    } catch (err: any) {
      toast.error(getApiError(err, "Save failed"));
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-100 dark:bg-slate-950 flex items-center justify-center">
        <div className="w-16 h-16 rounded-xl bg-slate-200 dark:bg-slate-800 animate-pulse" />
      </div>
    );
  }

  return (
    <AdminShell title="Store Settings" user={user}>
      <form onSubmit={save} className="space-y-6 max-w-4xl">
        {/* Store / Localization */}
        <section className="card p-5 space-y-4">
          <h2 className="flex items-center gap-2 font-semibold text-slate-900 dark:text-white">
            <Globe2 size={18} className="text-sky-600" /> Store Country &amp; Currency
          </h2>
          <div className="grid md:grid-cols-4 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                Store country (domestic)
              </label>
              <select
                value={store.country}
                onChange={(e) => handleCountryChange(e.target.value)}
                className="input text-sm"
              >
                {countries.map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                Currency
              </label>
              <select
                value={store.currency}
                onChange={(e) => {
                  const cur = COMMON_CURRENCIES.find((c) => c.code === e.target.value);
                  setStore({ ...store, currency: e.target.value, currency_symbol: cur?.symbol || store.currency_symbol });
                }}
                className="input text-sm"
              >
                {COMMON_CURRENCIES.map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.code}
                  </option>
                ))}
                {!COMMON_CURRENCIES.some((c) => c.code === store.currency) && (
                  <option value={store.currency}>{store.currency}</option>
                )}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                Currency symbol
              </label>
              <input
                value={store.currency_symbol}
                onChange={(e) => setStore({ ...store, currency_symbol: e.target.value })}
                className="input text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                Timezone
              </label>
              <input
                value={store.timezone}
                onChange={(e) => setStore({ ...store, timezone: e.target.value })}
                placeholder="e.g. UTC, Europe/London"
                className="input text-sm"
              />
            </div>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Domestic orders ship at the local rate; every other country pays the international rate.
            Prices display as {formatMoney(1000)} across the storefront.
          </p>
        </section>

        {/* Company */}
        <section className="card p-5 space-y-4">
          <h2 className="flex items-center gap-2 font-semibold text-slate-900 dark:text-white">
            <Building2 size={18} className="text-sky-600" /> Company &amp; Invoice Details
          </h2>
          <div className="grid md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                Company name
              </label>
              <input
                value={company.name}
                onChange={(e) => setCompany({ ...company, name: e.target.value })}
                className="input text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                Support email
              </label>
              <input
                value={company.support_email}
                onChange={(e) => setCompany({ ...company, support_email: e.target.value })}
                className="input text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                Support phone (international format)
              </label>
              <input
                value={company.support_phone}
                onChange={(e) => setCompany({ ...company, support_phone: e.target.value })}
                placeholder="+1 555 010 0000"
                className="input text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                Registered address
              </label>
              <input
                value={company.address}
                onChange={(e) => setCompany({ ...company, address: e.target.value })}
                className="input text-sm"
              />
            </div>
          </div>
        </section>

        {/* Banner / hero poster */}
        <section className="card p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="flex items-center gap-2 font-semibold text-slate-900 dark:text-white">
              <Megaphone size={18} className="text-sky-600" /> Homepage Poster &amp; Banner
            </h2>
            <span className="rounded-full bg-sky-50 px-2.5 py-1 text-[11px] font-semibold text-sky-700 dark:bg-sky-950/50 dark:text-sky-300">
              Auto-slides every 6s
            </span>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
              Hero poster photos
            </label>
            <ImageSlideshowEditor
              images={banner.images}
              onAdd={addBannerImages}
              onRemove={removeBannerImage}
            />
            <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
              The first photo is the cover. All photos fill the large homepage header and rotate
              automatically. Leave empty to keep the gradient background.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                Badge
              </label>
              <input
                value={banner.badge}
                onChange={(e) => setBanner({ ...banner, badge: e.target.value })}
                placeholder="e.g. AI-powered pricing"
                className="input text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                Title
              </label>
              <input
                value={banner.title}
                onChange={(e) => setBanner({ ...banner, title: e.target.value })}
                placeholder="e.g. Shop smarter, anywhere in the world"
                className="input text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                Subtitle
              </label>
              <input
                value={banner.subtitle}
                onChange={(e) => setBanner({ ...banner, subtitle: e.target.value })}
                placeholder="Short description under the title"
                className="input text-sm"
              />
            </div>
          </div>
        </section>

        {/* Posters */}
        <section className="card p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="flex items-center gap-2 font-semibold text-slate-900 dark:text-white">
              <ImageIcon size={18} className="text-sky-600" /> Poster Cards
            </h2>
            <span className="rounded-full bg-sky-50 px-2.5 py-1 text-[11px] font-semibold text-sky-700 dark:bg-sky-950/50 dark:text-sky-300">
              Photo slideshow per card
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Add up to {MAX_SLIDESHOW_IMAGES} photos to each card. When a card has multiple photos,
            they rotate automatically every 5 seconds. Cards without photos keep their gradient.
          </p>
          <div className="grid md:grid-cols-2 gap-4">
            {posters.map((p, i) => (
              <div key={i} className="border dark:border-slate-700 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wide text-slate-400">
                    Poster {i + 1}
                  </span>
                  <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
                    <input
                      type="checkbox"
                      checked={p.visible}
                      onChange={(e) => updatePoster(i, { visible: e.target.checked })}
                    />
                    Visible
                  </label>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    value={p.title}
                    onChange={(e) => updatePoster(i, { title: e.target.value })}
                    placeholder="Title"
                    className="input text-sm"
                  />
                  <input
                    value={p.subtitle}
                    onChange={(e) => updatePoster(i, { subtitle: e.target.value })}
                    placeholder="Subtitle"
                    className="input text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                    Accent color (used when no photos are added)
                  </label>
                  <select
                    value={p.accent}
                    onChange={(e) => updatePoster(i, { accent: e.target.value })}
                    className="input text-sm"
                  >
                    {ACCENTS.map((a) => (
                      <option key={a} value={a}>
                        {a}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                    Photos
                  </label>
                  <ImageSlideshowEditor
                    images={p.images || []}
                    onAdd={(urls) => addPosterImages(i, urls)}
                    onRemove={(url) => removePosterImage(i, url)}
                  />
                </div>
                <div
                  className={`relative overflow-hidden rounded-lg p-3 text-white text-xs bg-gradient-to-br ${p.accent} ${
                    p.visible ? "" : "opacity-40"
                  }`}
                >
                  {p.images?.[0] && (
                    <>
                      <img
                        src={p.images[0]}
                        alt=""
                        className="absolute inset-0 w-full h-full object-cover"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/35 to-black/10" />
                    </>
                  )}
                  <div className="relative">
                    <p className="font-bold uppercase tracking-widest">{p.title || "Title"}</p>
                    <p className="mt-1 text-white/90">{p.subtitle || "Subtitle"}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Delivery */}
        <section className="card p-5 space-y-4">
          <h2 className="flex items-center gap-2 font-semibold text-slate-900 dark:text-white">
            <Truck size={18} className="text-sky-600" /> Delivery Pricing
          </h2>
          <div className="grid md:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                Domestic charge
              </label>
              <div className="flex items-center gap-1">
                <span className="text-slate-500 dark:text-slate-400 text-sm">{store.currency_symbol}</span>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={delivery.local_charge}
                  onChange={(e) => setDelivery({ ...delivery, local_charge: parseFloat(e.target.value) || 0 })}
                  className="input text-sm"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                International charge
              </label>
              <div className="flex items-center gap-1">
                <span className="text-slate-500 dark:text-slate-400 text-sm">{store.currency_symbol}</span>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={delivery.international_charge}
                  onChange={(e) => setDelivery({ ...delivery, international_charge: parseFloat(e.target.value) || 0 })}
                  className="input text-sm"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                Free delivery threshold ({store.currency_symbol})
              </label>
              <div className="flex items-center gap-1">
                <span className="text-slate-500 dark:text-slate-400 text-sm">{store.currency_symbol}</span>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={delivery.free_delivery_threshold}
                  onChange={(e) => setDelivery({ ...delivery, free_delivery_threshold: parseFloat(e.target.value) || 0 })}
                  className="input text-sm"
                />
              </div>
            </div>
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
            <input
              type="checkbox"
              checked={delivery.free_delivery_enabled}
              onChange={(e) => setDelivery({ ...delivery, free_delivery_enabled: e.target.checked })}
            />
            Enable free delivery on orders at or above the threshold
          </label>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Domestic ({store.country}): {formatMoney(delivery.local_charge)} · International:{" "}
            {formatMoney(delivery.international_charge)}
          </p>
        </section>

        {/* Payment methods */}
        <section className="card p-5 space-y-4">
          <h2 className="flex items-center gap-2 font-semibold text-slate-900 dark:text-white">
            <CreditCard size={18} className="text-sky-600" /> Payment Methods
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Enabled methods appear at checkout. Configure provider credentials (Stripe, PayPal,
            bKash…) in the backend environment.
          </p>
          <div className="grid md:grid-cols-2 gap-2">
            {paymentMethods.map((m) => (
              <label
                key={m.id}
                className="flex items-center justify-between gap-3 border dark:border-slate-700 rounded-xl px-4 py-3 cursor-pointer"
              >
                <span className="text-sm text-slate-700 dark:text-slate-300">{m.label || m.id}</span>
                <input
                  type="checkbox"
                  checked={!!m.enabled}
                  onChange={(e) => updatePaymentMethod(m.id, e.target.checked)}
                />
              </label>
            ))}
          </div>
        </section>

        <div className="flex justify-end">
          <button type="submit" disabled={saving} className="btn-primary inline-flex gap-2 disabled:opacity-50">
            <Save size={16} /> {saving ? "Saving..." : "Save Settings"}
          </button>
        </div>
      </form>

      <div className="mt-6">
        <TwoFactorCard scope="admin" />
      </div>
    </AdminShell>
  );
}
