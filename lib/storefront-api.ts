import { apiCall } from "@/lib/_core/api";

export type StorefrontSlide = { id: string; title: string; subtitle: string; ctaLabel: string; imageUrl: string; storageKey: string; isActive: boolean; sortOrder: number };
export type StorefrontCircle = { id: string; title: string; targetCategory: string; imageUrl: string; storageKey: string; isActive: boolean; sortOrder: number };
export type StorefrontTab = { id: string; title: string; searchPlaceholder: string; isActive: boolean; sortOrder: number; slides: StorefrontSlide[]; circles: StorefrontCircle[] };
type ImagePayload = { dataUrl: string; fileName: string };
export async function getStorefront() { return (await apiCall<{ tabs: StorefrontTab[] }>("/api/storefront")).tabs; }
export async function getAdminStorefront() { return (await apiCall<{ tabs: StorefrontTab[] }>("/api/admin/storefront")).tabs; }
export async function createTab(payload: { title: string; searchPlaceholder: string }) { return apiCall<{ tabs: StorefrontTab[] }>("/api/admin/storefront/tabs", { method: "POST", body: JSON.stringify(payload) }); }
export async function updateTab(id: string, payload: Partial<{ title: string; searchPlaceholder: string; isActive: boolean; sortOrder: number }>) { return apiCall<{ tabs: StorefrontTab[] }>(`/api/admin/storefront/tabs/${id}`, { method: "PATCH", body: JSON.stringify(payload) }); }
export async function deleteTab(id: string) { return apiCall<{ tabs: StorefrontTab[] }>(`/api/admin/storefront/tabs/${id}`, { method: "DELETE" }); }
export async function createSlide(tabId: string, payload: { title: string; subtitle: string; ctaLabel: string; image: ImagePayload }) { return apiCall<{ tabs: StorefrontTab[] }>(`/api/admin/storefront/tabs/${tabId}/slides`, { method: "POST", body: JSON.stringify(payload) }); }
export async function updateSlide(id: string, payload: Partial<{ isActive: boolean; sortOrder: number }>) { return apiCall<{ tabs: StorefrontTab[] }>(`/api/admin/storefront/slides/${id}`, { method: "PATCH", body: JSON.stringify(payload) }); }
export async function deleteSlide(id: string) { return apiCall<{ tabs: StorefrontTab[] }>(`/api/admin/storefront/slides/${id}`, { method: "DELETE" }); }
export async function createCircle(tabId: string, payload: { title: string; targetCategory: string; image?: ImagePayload }) { return apiCall<{ tabs: StorefrontTab[] }>(`/api/admin/storefront/tabs/${tabId}/circles`, { method: "POST", body: JSON.stringify(payload) }); }
export async function updateCircle(id: string, payload: Partial<{ isActive: boolean; sortOrder: number }>) { return apiCall<{ tabs: StorefrontTab[] }>(`/api/admin/storefront/circles/${id}`, { method: "PATCH", body: JSON.stringify(payload) }); }
export async function deleteCircle(id: string) { return apiCall<{ tabs: StorefrontTab[] }>(`/api/admin/storefront/circles/${id}`, { method: "DELETE" }); }
