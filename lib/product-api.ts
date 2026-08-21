import { apiCall } from "@/lib/_core/api";

export type StoreProduct = {
  id: string;
  productCode: string;
  name: string;
  category: string;
  categories: string[];
  description: string;
  details: string;
  material: string;
  price: number;
  originalPrice: number;
  discountPercent: number;
  shippingNote: string;
  isTrending: boolean;
  trendTags: string[];
  images: { id: number; storageKey: string; url: string; sortOrder: number }[];
  colors: { id: number; name: string; hex: string }[];
  sizes: { id: number; label: string; stock: number }[];
  rating: number;
  reviews: number;
  reviewsList: { id: number; rating: number; body: string; selectedColor: string | null; selectedSize: string | null; helpfulCount: number; author: string; createdAt: string }[];
  vendor: { id: number; name: string; slug: string; description: string; logoUrl?: string | null; rating?: number };
  returnPolicy: string;
};

export type ProductEditorPayload = { productCode?: string; name: string; category: string; categories: string[]; description: string; details: string; material: string; price: number; discountPercent: number; shippingNote: string; isTrending: boolean; trendTags: string[]; isPublished: boolean; colors: { name: string; hex: string }[]; sizes: { label: string; stock: number }[]; images?: { dataUrl: string; fileName: string; sortOrder: number }[]; existingImages?: { storageKey: string; url: string; sortOrder: number }[]; newImages?: { dataUrl: string; fileName: string; sortOrder: number }[]; };

type DjangoProduct = {
  id: number;
  sku?: string;
  name: string;
  description?: string;
  details?: unknown;
  price?: string | number;
  sale_price?: string | number | null;
  effective_price?: string | number;
  discount_percent?: number;
  currency?: string;
  stock?: number;
  colors?: Array<{ id?: number; name: string; hex?: string }>;
  sizes?: Array<{ id?: number; label: string; stock?: number }>;
  hashtags?: string[];
  is_trending?: boolean;
  rating?: string | number;
  reviews_count?: number;
  categories?: Array<{ id?: number; name: string; slug?: string }>;
  vendor?: { id?: number; store_name?: string; slug?: string; description?: string; logo_url?: string | null };
  main_image_url?: string | null;
  images?: Array<{ id?: number; url?: string; storageKey?: string; sortOrder?: number } | string>;
  gallery?: Array<{ id?: number; url?: string; alt?: string; sort_order?: number; is_primary?: boolean }>;
  brand?: string;
  material?: string;
  shipping_note?: string;
  return_policy?: string;
  sold_count?: number;
};

function detailsText(value: unknown): string {
  if (!value) return "";
  if (typeof value === "string") return value;
  if (typeof value === "object") return Object.entries(value as Record<string, unknown>).map(([key, item]) => `${key}: ${String(item)}`).join("\n");
  return String(value);
}

function numberValue(value: string | number | null | undefined): number {
  const result = Number(value ?? 0);
  return Number.isFinite(result) ? result : 0;
}

function normalizeProduct(product: DjangoProduct): StoreProduct {
  const basePrice = numberValue(product.price);
  const finalPrice = numberValue(product.effective_price ?? product.sale_price ?? product.price);
  const rawImages = product.gallery?.length ? product.gallery : (product.images ?? []);
  const imageItems = rawImages.map((image, index) => {
    const item = typeof image === "string" ? { url: image } : image;
    return {
      id: Number(item.id ?? index),
      storageKey: "storageKey" in item ? String(item.storageKey ?? "") : "",
      url: String(item.url ?? ""),
      sortOrder: Number("sort_order" in item ? item.sort_order ?? index : "sortOrder" in item ? item.sortOrder ?? index : index),
    };
  }).filter((image) => image.url);
  if (product.main_image_url && !imageItems.some((image) => image.url === product.main_image_url)) {
    imageItems.unshift({ id: -1, storageKey: "", url: product.main_image_url, sortOrder: -1 });
  }
  return {
    id: String(product.id),
    productCode: product.sku ?? `SKU-${product.id}`,
    name: product.name,
    category: product.categories?.[0]?.name ?? "عام",
    categories: (product.categories ?? []).map((category) => category.name),
    description: product.description ?? "",
    details: detailsText(product.details),
    material: product.material ?? "",
    price: finalPrice,
    originalPrice: basePrice,
    discountPercent: Number(product.discount_percent ?? (basePrice > finalPrice ? Math.round((1 - finalPrice / basePrice) * 100) : 0)),
    shippingNote: product.shipping_note ?? "",
    isTrending: Boolean(product.is_trending),
    trendTags: product.hashtags ?? [],
    images: imageItems,
    colors: (product.colors ?? []).map((color, index) => ({ id: Number(color.id ?? index), name: color.name, hex: color.hex ?? "#E5E5E5" })),
    sizes: (product.sizes ?? []).map((size, index) => ({ id: Number(size.id ?? index), label: size.label, stock: Number(size.stock ?? product.stock ?? 0) })),
    rating: numberValue(product.rating),
    reviews: Number(product.reviews_count ?? 0),
    reviewsList: [],
    vendor: { id: Number(product.vendor?.id ?? 0), name: product.vendor?.store_name ?? "متجر موثوق", slug: product.vendor?.slug ?? "", description: product.vendor?.description ?? "", logoUrl: product.vendor?.logo_url ?? null },
    returnPolicy: product.return_policy ?? "إرجاع خلال 7 أيام حسب سياسة المتجر",
  };
}

export async function getProducts(query = "") {
  const suffix = query ? `?q=${encodeURIComponent(query)}` : "";
  const response = await apiCall<DjangoProduct[] | { results?: DjangoProduct[]; products?: DjangoProduct[] }>(`/api/products/${suffix}`);
  const items = Array.isArray(response) ? response : (response.results ?? response.products ?? []);
  return items.map(normalizeProduct);
}

export async function getProduct(id: string) {
  const response = await apiCall<DjangoProduct>(`/api/products/${encodeURIComponent(id)}/`);
  return { product: normalizeProduct(response), similar: [] as StoreProduct[] };
}

export async function getAdminProducts() { return getProducts(); }
export async function createProduct(payload: ProductEditorPayload) { return apiCall<{ product: StoreProduct }>("/api/products/", { method: "POST", body: JSON.stringify(payload) }); }
export async function updateProduct(id: string, payload: ProductEditorPayload) { return apiCall<{ product: StoreProduct }>(`/api/products/${encodeURIComponent(id)}/`, { method: "PATCH", body: JSON.stringify(payload) }); }
