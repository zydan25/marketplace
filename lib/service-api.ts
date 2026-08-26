import { djangoApi } from "@/lib/django-api";

export type ServiceField = { id: number; key: string; label: string; field_type: string; placeholder: string; help_text: string; is_required: boolean; options: unknown[]; sort_order: number };
export type Service = { id: number; name: string; slug: string; category: number; category_name: string; image_url?: string | null; banner_url?: string | null; description: string; price: string; currency: string; is_active: boolean; is_featured: boolean; sort_order: number; config: Record<string, unknown>; fields: ServiceField[] };
export type ServiceCategory = { id: number; name: string; parent: number | null; image_url?: string | null; description: string; sort_order: number; is_active: boolean; children_count: number };

export async function getServiceCategories(): Promise<ServiceCategory[]> { const data = await djangoApi<{ results?: ServiceCategory[] } | ServiceCategory[]>("/api/service-categories/"); return Array.isArray(data) ? data : (data.results ?? []); }
export async function getServices(category?: number): Promise<Service[]> { const endpoint = category ? `/api/services/?category=${category}` : "/api/services/"; const data = await djangoApi<{ results?: Service[] } | Service[]>(endpoint); return Array.isArray(data) ? data : (data.results ?? []); }
export async function getService(slug: string): Promise<Service> { return djangoApi<Service>(`/api/services/${encodeURIComponent(slug)}/`); }
export async function submitService(service: number, data: Record<string, unknown>): Promise<unknown> { return djangoApi("/api/service-submissions/", { method: "POST", body: JSON.stringify({ service, data }) }); }
