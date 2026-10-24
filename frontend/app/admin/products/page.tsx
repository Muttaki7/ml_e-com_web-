"use client";

import { useEffect, useRef, useState } from "react";
import { adminApi, formatMoney, getApiError, mediaUrl } from "@/lib/api";
import { useAdminAuth } from "@/lib/useAdminAuth";
import { AdminShell } from "@/components/AdminShell";
import toast from "react-hot-toast";
import { Trash2 } from "lucide-react";

export default function AdminProductsPage() {
  const { user, loading } = useAdminAuth();
  const [products, setProducts] = useState<any[]>([]);
  const [q, setQ] = useState("");
  const qRef = useRef("");
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [imageInput, setImageInput] = useState(0);
  const empty = {
    name: "",
    sku: "",
    brand: "",
    selling_price: "",
    purchase_price: "",
    discount_percent: "0",
    stock_quantity: "10",
    min_stock_level: "5",
    is_featured: false,
    description: "",
    tags: [] as string[],
    images: [] as string[],
  };
  const [form, setForm] = useState(empty);
  const [tagInput, setTagInput] = useState("");
  const tagInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!loading) {
      load();
    }
    const timer = setInterval(() => {
      load();
    }, 5 * 60 * 1000);
    return () => clearInterval(timer);
  }, [loading]);

  async function load() {
    try {
      const params: any = { limit: 100 };
      if (qRef.current) params.q = qRef.current;
      const r = await adminApi.products(params);
      setProducts(r.data || []);
    } catch {
      setProducts([]);
    }
  }

  async function handleImageUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    setImageInput((x) => x + 1); // allow re-selecting the same file
    if (!file) return;
    setUploading(true);
    try {
      const r = await adminApi.uploadProductImage(file);
      setForm((f) => ({ ...f, images: [...f.images, r.data.url] }));
      toast.success("Image uploaded");
    } catch (err: any) {
      toast.error(getApiError(err, "Image upload failed"));
    } finally {
      setUploading(false);
    }
  }

  function removeImage(url: string) {
    setForm((f) => ({ ...f, images: f.images.filter((i) => i !== url) }));
  }

  function addTag() {
    const t = tagInput.trim();
    if (t && !form.tags.includes(t)) setForm((f) => ({ ...f, tags: [...f.tags, t] }));
    setTagInput("");
  }

  function removeTag(t: string) {
    setForm((f) => ({ ...f, tags: f.tags.filter((x) => x !== t) }));
  }

  async function removeProduct(id: string) {
    if (!window.confirm("Delete this product permanently? This hides it from the storefront.")) return;
    setDeleting(id);
    try {
      await adminApi.deleteProduct(id);
      toast.success("Product removed");
      load();
    } catch (err: any) {
      toast.error(getApiError(err, "Delete failed"));
    } finally {
      setDeleting(null);
    }
  }

  async function createProduct(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await adminApi.createProduct({
        name: form.name,
        sku: form.sku || `SKU-${Date.now().toString().slice(-5)}`,
        brand: form.brand || undefined,
        selling_price: parseFloat(form.selling_price),
        purchase_price: parseFloat(form.purchase_price),
        discount_percent: parseFloat(form.discount_percent) || 0,
        stock_quantity: parseInt(form.stock_quantity) || 0,
        min_stock_level: parseInt(form.min_stock_level) || 5,
        is_featured: form.is_featured,
        description: form.description || undefined,
        tags: form.tags,
        images: form.images,
      });
      toast.success("Product created");
      setForm(empty);
      setShowForm(false);
      load();
    } catch (err: any) {
      toast.error(getApiError(err, "Create failed"));
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-100 flex items-center justify-center">
        <div className="w-16 h-16 rounded-xl bg-slate-200 animate-pulse" />
      </div>
    );
  }

  return (
    <AdminShell title="Products" user={user}>
      <div className="space-y-6">
        <div className="flex flex-wrap items-center gap-2">
          <input
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              qRef.current = e.target.value;
            }}
            onKeyDown={(e) => e.key === "Enter" && load()}
            placeholder="Search products..."
            className="input !py-2 text-sm w-64"
          />
          <button
            onClick={() => setShowForm((s) => !s)}
            className="btn-primary !py-2 text-sm inline-flex"
          >
            {showForm ? "Close Form" : "+ New Product"}
          </button>
        </div>
        {showForm && (
            <form onSubmit={createProduct} className="card p-5 grid md:grid-cols-3 gap-3">
              <input
                required
                placeholder="Product name"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="input text-sm"
              />
              <input
                required
                placeholder="SKU"
                value={form.sku}
                onChange={(e) => setForm({ ...form, sku: e.target.value })}
                className="input text-sm"
              />
              <input
                placeholder="Brand"
                value={form.brand}
                onChange={(e) => setForm({ ...form, brand: e.target.value })}
                className="input text-sm"
              />
              <input
                required
                type="number"
                step="0.01"
                placeholder="Selling price"
                value={form.selling_price}
                onChange={(e) => setForm({ ...form, selling_price: e.target.value })}
                className="input text-sm"
              />
              <input
                required
                type="number"
                step="0.01"
                placeholder="Purchase price"
                value={form.purchase_price}
                onChange={(e) => setForm({ ...form, purchase_price: e.target.value })}
                className="input text-sm"
              />
              <input
                type="number"
                placeholder="Discount %"
                value={form.discount_percent}
                onChange={(e) => setForm({ ...form, discount_percent: e.target.value })}
                className="input text-sm"
              />
              <input
                type="number"
                placeholder="Stock"
                value={form.stock_quantity}
                onChange={(e) => setForm({ ...form, stock_quantity: e.target.value })}
                className="input text-sm"
              />
              <input
                type="number"
                placeholder="Min stock level"
                value={form.min_stock_level}
                onChange={(e) => setForm({ ...form, min_stock_level: e.target.value })}
                className="input text-sm"
              />
              <div
                className="md:col-span-2"
                onClick={() => tagInputRef.current?.focus()}
              >
                <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                  Tags
                </p>
                <div className="flex flex-wrap items-center gap-1.5 border rounded-lg px-2 py-1.5 cursor-text">
                  {form.tags.map((t) => (
                    <span
                      key={t}
                      className="inline-flex items-center gap-1 bg-sky-100 dark:bg-sky-500/10 text-sky-700 dark:text-sky-400 text-xs font-medium rounded px-2 py-0.5"
                    >
                      {t}
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          removeTag(t);
                        }}
                        className="hover:text-rose-600 leading-none"
                        title={`Remove ${t}`}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                  <input
                    ref={tagInputRef}
                    value={tagInput}
                    onChange={(e) => setTagInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === ",") {
                        e.preventDefault();
                        addTag();
                      } else if (e.key === "Backspace" && !tagInput && form.tags.length) {
                        removeTag(form.tags[form.tags.length - 1]);
                      }
                    }}
                    onBlur={addTag}
                    placeholder={form.tags.length ? "" : "Type a tag, press Enter..."}
                    className="flex-1 min-w-[9rem] bg-transparent outline-none text-sm py-0.5"
                  />
                </div>
              </div>
              <textarea
                placeholder="Description"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                className="border rounded-lg px-3 py-2 text-sm md:col-span-3"
              />
              <div className="md:col-span-3">
                <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                  Product images (JPEG / PNG / WEBP / GIF, max 5 MB each)
                </p>
                <div className="flex flex-wrap items-center gap-2">
                  {form.images.map((url) => (
                    <div key={url} className="relative">
                      <img
                        src={mediaUrl(url)}
                        alt="product"
                        className="w-16 h-16 rounded-lg border dark:border-slate-700 object-cover"
                      />
                      <button
                        type="button"
                        onClick={() => removeImage(url)}
                        className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-rose-600 text-white text-xs leading-none"
                        title="Remove image"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                  <label
                    className={`w-16 h-16 rounded-lg border-2 border-dashed flex items-center justify-center cursor-pointer text-xs text-slate-400 hover:border-sky-400 dark:border-slate-700 ${
                      uploading ? "opacity-50 pointer-events-none" : ""
                    }`}
                  >
                    {uploading ? "…" : "+"}
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp,image/gif"
                      className="hidden"
                      onChange={handleImageUpload}
                      key={imageInput}
                    />
                  </label>
                </div>
              </div>
              <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={form.is_featured}
                  onChange={(e) => setForm({ ...form, is_featured: e.target.checked })}
                />
                Featured
              </label>
              <div className="md:col-span-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="btn-outline text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="btn-primary text-sm disabled:opacity-50"
                >
                  {saving ? "Saving..." : "Create Product"}
                </button>
              </div>
            </form>
          )}

          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 dark:text-slate-400 border-b dark:border-slate-700">
                  <th className="py-3 px-4">Product</th>
                  <th>SKU</th>
                  <th>Tags</th>
                  <th>Price</th>
                  <th>Stock</th>
                  <th>Status</th>
                  {user?.is_main_admin && <th>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {products.map((p) => (
                  <tr key={p.id} className="border-b dark:border-slate-700 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-800/50">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-3">
                        {p.images?.[0] ? (
                          <img
                            src={mediaUrl(p.images[0])}
                            alt={p.name}
                            className="w-10 h-10 rounded-lg border dark:border-slate-700 object-cover"
                          />
                        ) : (
                          <div className="w-10 h-10 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-xs text-slate-400">
                            {p.name?.slice(0, 2)}
                          </div>
                        )}
                        <div>
                          <p className="font-medium text-slate-900 dark:text-white">{p.name}</p>
                          <p className="text-xs text-slate-400">
                            {p.brand || "—"} {p.images?.length ? `· ${p.images.length} img` : ""}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="text-slate-500 dark:text-slate-400">{p.sku}</td>
                    <td className="text-slate-600 dark:text-slate-300">
                      {p.tags?.length ? (
                        <div className="flex flex-wrap gap-1">
                          {p.tags.map((t: string) => (
                            <span
                              key={t}
                              className="text-xs bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 rounded px-2 py-0.5"
                            >
                              {t}
                            </span>
                          ))}
                        </div>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="font-semibold text-slate-900 dark:text-white">{formatMoney(p.final_price)}</td>
                    <td className="text-slate-700 dark:text-slate-300">
                      <span
                        className={p.stock_quantity <= p.min_stock_level ? "text-rose-600 font-medium" : ""}
                      >
                        {p.stock_quantity}
                      </span>
                      <span className="text-xs text-slate-400"> / min {p.min_stock_level}</span>
                    </td>
                    <td>
                      <span className="text-xs bg-sky-50 dark:bg-sky-500/10 text-sky-700 dark:text-sky-400 rounded px-2 py-0.5">
                        {p.status}
                      </span>
                    </td>
                    {user?.is_main_admin && (
                      <td>
                        <button
                          onClick={() => removeProduct(p.id)}
                          disabled={deleting === p.id}
                          className="inline-flex items-center gap-1 text-xs text-rose-600 hover:text-rose-700 hover:bg-rose-50 dark:hover:bg-rose-500/10 rounded-lg px-2 py-1 disabled:opacity-50"
                        >
                          <Trash2 size={13} /> {deleting === p.id ? "Removing..." : "Remove"}
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
                {products.length === 0 && (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-slate-400">
                      No products found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
    </AdminShell>
  );
}