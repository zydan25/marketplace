import { djangoApi } from "@/lib/django-api";

export type ServiceField = { key: string; label: string; type: string; required: boolean; secret: boolean; choices: string[]; default: unknown; validation: Record<string, unknown> };
export type ServiceItem = { id: number; type: "service_options" | "telecom_denominations" | "telecom_plans" | "game_products" | "digital_products"; name: string; price?: string; currency: string; metadata: Record<string, unknown>; availability: { available: boolean; reason?: string; quantity?: string } };
export type Service = { id: number; code: string; name: string; description: string; service_kind: string; requires_balance: boolean; pricing_mode: string; price: string; currency: string; min_amount: string | null; max_amount: string | null; request_schema: Record<string, unknown>; response_schema: Record<string, unknown>; fields: ServiceField[]; items: ServiceItem[]; categoryName?: string; categorySlug?: string };
export type ServiceCategory = { id: number; name: string; slug: string; parent_id: number | null; services: Service[]; children: ServiceCategory[] };
export type ServiceMainCategory = { id: number; name: string; slug: string; icon: string; categories: ServiceCategory[] };
export type ServiceCatalogResponse = { version: string; categories: ServiceMainCategory[] };

export async function getServiceCatalog() { return djangoApi<ServiceCatalogResponse>("/api/v2/services/catalog/"); }
export async function submitServiceRequest(input: { serviceId: number; itemId?: number; itemType?: ServiceItem["type"]; payload?: Record<string, unknown> }) {
  return djangoApi<{ id: string; service: string; service_kind: string; status: string; amount: string; currency: string; provider_transid?: string | null; provider_transaction_id?: string | null; error_code?: string | null; error_message?: string | null }>("/api/v2/services/requests/", { method: "POST", body: JSON.stringify({ service_id: input.serviceId, item_id: input.itemId, item_type: input.itemType, payload: input.payload ?? {} }) });
}
export function flattenServiceCategories(main: ServiceMainCategory) {
  const result: Array<Service & { categoryName: string; categorySlug: string }> = [];
  const visit = (category: ServiceCategory) => { category.services.forEach((service) => result.push({ ...service, categoryName: category.name, categorySlug: category.slug })); category.children.forEach(visit); };
  main.categories.forEach(visit);
  return result;
}
export function formatServiceMoney(value: string | number, currency = "YER") { const amount = Number(value ?? 0); if (!Number.isFinite(amount)) return `${value} ${currency}`; return `${new Intl.NumberFormat("ar-YE").format(amount)} ${currency === "YER" ? "ر.ي" : currency}`; }
