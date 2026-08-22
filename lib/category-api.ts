import { apiCall } from "@/lib/_core/api";

export type StoreCategory = { id: number; name: string; slug: string; image?: string | null; parent?: number | null; is_active?: boolean; sort_order?: number };

export async function getCategories() {
  const response = await apiCall<{ results?: StoreCategory[] } | StoreCategory[]>("/api/categories/");
  const items = Array.isArray(response) ? response : (response.results ?? []);
  return items.filter((category) => category.is_active !== false).sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
}
