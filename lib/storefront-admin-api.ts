import { djangoApi } from "@/lib/django-api";

export type AdminCategory = { id: number; name: string; slug: string; parent: number | null; image_url?: string | null; is_active: boolean; sort_order: number };

export async function getAdminCategories(): Promise<AdminCategory[]> {
  const data = await djangoApi<{ results?: AdminCategory[] } | AdminCategory[]>("/api/categories/");
  return Array.isArray(data) ? data : (data.results ?? []);
}

export async function createAdvancedSection(payload: {
  title: string;
  sectionType: string;
  searchPlaceholder?: string;
  vendorId?: number;
  config?: Record<string, unknown>;
}) {
  await djangoApi("/api/storefront-sections/", {
    method: "POST",
    body: JSON.stringify({
      title: payload.title,
      section_type: payload.sectionType,
      vendor_id: payload.vendorId,
      config: {
        searchPlaceholder: payload.searchPlaceholder ?? "ابحث عن منتج أو متجر",
        slides: [],
        circles: [],
        cards: [],
        actions: [],
        promo: { enabled: false },
        ...(payload.config ?? {}),
      },
      sort_order: Date.now(),
      is_visible: true,
    }),
  });
}

export async function patchSectionConfig(id: string, config: Record<string, unknown>) {
  return djangoApi(`/api/storefront-sections/${encodeURIComponent(id)}/`, {
    method: "PATCH",
    body: JSON.stringify({ config }),
  });
}
