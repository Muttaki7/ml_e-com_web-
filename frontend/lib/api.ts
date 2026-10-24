import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    const type = localStorage.getItem("token_type"); // customer | admin
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      // optional: try refresh
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
    }
    return Promise.reject(error);
  }
);

/**
 * Safely extract a human readable error message from an API error.
 * FastAPI returns arrays of validation objects ({type, loc, msg, input, ctx})
 * for 422 responses which react-hot-toast cannot render — this keeps the
 * message a plain string.
 */
export function getApiError(err: any, fallback = "Something went wrong"): string {
  const detail = err?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((d: any) => (typeof d?.msg === "string" ? d.msg : null))
      .filter(Boolean);
    if (parts.length) return parts.join("; ");
  }
  if (detail && typeof detail === "object") {
    if (typeof detail.message === "string") return detail.message;
    if (typeof detail.detail === "string") return detail.detail;
    if (typeof detail.error === "string") return detail.error;
  }
  if (typeof err?.message === "string") return err.message;
  return fallback;
}

/** Trigger a browser download from an axios blob response. */
export function downloadBlob(response: any, fallbackName: string) {
  const blob = response?.data instanceof Blob ? response.data : new Blob([response?.data]);
  let filename = fallbackName;
  const header = response?.headers?.["content-disposition"] as string | undefined;
  if (header) {
    const match = header.match(/filename\*?=(?:UTF-8'')?["']?([^"';]+)/i);
    if (match && match[1]) filename = decodeURIComponent(match[1].trim());
  }
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
}

// Auth helpers
export const authApi = {
  customerRegister: (data: any) => api.post("/auth/customer/register", data),
  customerLogin: (data: any) => api.post("/auth/customer/login", data),
  customer2faVerify: (data: any) => api.post("/auth/customer/2fa/verify", data),
  customer2faSetup: () => api.post("/auth/customer/2fa/setup"),
  customer2faConfirm: (code: string) => api.post("/auth/customer/2fa/confirm", { code }),
  customer2faDisable: (code: string) => api.post("/auth/customer/2fa/disable", { code }),
  adminLogin: (data: any) => api.post("/auth/admin/login", data),
  admin2faVerify: (data: any) => api.post("/auth/admin/2fa/verify", data),
  admin2faSetup: () => api.post("/auth/admin/2fa/setup"),
  admin2faConfirm: (code: string) => api.post("/auth/admin/2fa/confirm", { code }),
  adminMe: () => api.get("/auth/admin/me"),
};

export const productApi = {
  list: (params?: any) => api.get("/products", { params }),
  get: (id: string) => api.get(`/products/${id}`),
  categories: () => api.get("/categories"),
  brands: () => api.get("/brands"),
};

export const settingsApi = {
  public: () => api.get("/settings/public"),
};

export const metaApi = {
  countries: () => api.get("/meta/countries"),
};

export const orderApi = {
  checkout: (data: any) => api.post("/orders/checkout", data),
  myOrders: () => api.get("/orders/my"),
  myInvoice: (orderId: string) =>
    api.get(`/orders/my/${orderId}/invoice`, { responseType: "blob" }),
};

export const adminApi = {
  dashboard: () => api.get("/analytics/dashboard"),
  salesByDay: (days = 30) => api.get("/analytics/sales-by-day", { params: { days } }),
  profitByCategory: () => api.get("/analytics/profit-by-category"),
  bi: () => api.get("/analytics/business-intelligence"),
  orders: (params?: any) => api.get("/admin/orders", { params }),
  updateOrderStatus: (id: string, status: string) =>
    api.patch(`/admin/orders/${id}/status`, null, { params: { status } }),
  orderInvoice: (orderId: string) =>
    api.get(`/admin/orders/${orderId}/invoice`, { responseType: "blob" }),
  products: (params?: any) => api.get("/products", { params }),
  createProduct: (data: any) => api.post("/admin/products", data),
  updateProduct: (id: string, data: any) => api.patch(`/admin/products/${id}`, data),
  deleteProduct: (id: string) => api.delete(`/admin/products/${id}`),
  uploadProductImage: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return api.post("/admin/products/upload-image", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  adminCategories: () => api.get("/admin/categories"),
  createCategory: (data: any) => api.post("/admin/categories", data),
  deleteCategory: (id: string) => api.delete(`/admin/categories/${id}`),
  mlDemand: (id: string) => api.get(`/ml/demand/${id}`),
  mlRecommendations: () => api.get("/ml/recommendations/purchase"),
  mlBatchForecast: (limit = 30) => api.post("/ml/forecast/batch", null, { params: { limit } }),
  admins: () => api.get("/admins"),
  createAdmin: (data: any) => api.post("/admins", data),
  disableAdmin: (id: string) => api.post(`/admins/${id}/disable`),
  settings: () => api.get("/admin/settings"),
  updateSettings: (data: any) => api.put("/admin/settings", data),
  uploadSettingsImage: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return api.post("/admin/settings/upload-image", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
};

// ---------- Global storefront settings (cached) ----------
let cachedPublicSettings: any = null;

/** Fetch (and cache) public store settings: currency, store country, payments, delivery. */
export async function getStoreSettings(force = false): Promise<any> {
  if (!cachedPublicSettings || force) {
    const res = await settingsApi.public();
    cachedPublicSettings = res.data;
  }
  return cachedPublicSettings;
}

/** Synchronous peek at the store currency; "USD" until the first fetch resolves. */
export function peekCurrency(): string {
  return cachedPublicSettings?.store?.currency || "USD";
}

/** Format an amount in the store currency (or a given ISO 4217 currency). */
export function formatMoney(amount: number, currency?: string) {
  const cur = currency || peekCurrency();
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: cur,
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(amount ?? 0);
  } catch {
    return `${cur} ${(amount ?? 0).toLocaleString()}`;
  }
}