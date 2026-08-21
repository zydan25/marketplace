import { apiCall } from "@/lib/_core/api";

export type StorefrontSlide = { id: string; title: string; subtitle: string; ctaLabel: string; imageUrl: string; storageKey: string; isActive: boolean; sortOrder: number };
export type StorefrontCircle = { id: string; title: string; targetCategory: string; imageUrl: string; storageKey: string; isActive: boolean; sortOrder: number };
export type StorefrontPromo = { flashTitle: string; flashSubtitle: string; flashMode: string; freeShippingTitle: string; freeShippingSubtitle: string; freeShippingCategory: string };
export type StorefrontTab = { id: string; title: string; searchPlaceholder: string; isActive: boolean; sortOrder: number; slides: StorefrontSlide[]; circles: StorefrontCircle[]; promo?: StorefrontPromo };
type ImagePayload = { dataUrl: string; fileName: string };
type ConfigRecord = Record<string, unknown>;
type RawSection = { id: number | string; title?: string; section_type?: string; type?: string; vendor?: number | null; config?: ConfigRecord; sort_order?: number; is_visible?: boolean };

type SectionsResponse = RawSection[] | { results?: RawSection[]; data?: RawSection[] };

function asRecord(value: unknown): ConfigRecord {
  return value && typeof value === "object" && !Array.isArray(value) ? value as ConfigRecord : {};
}

function asArray(value: unknown): ConfigRecord[] {
  return Array.isArray(value) ? value.filter((item): item is ConfigRecord => Boolean(item) && typeof item === "object") : [];
}

function text(value: unknown, fallback = "") {
  return typeof value === "string" ? value : value == null ? fallback : String(value);
}

function bool(value: unknown, fallback = true) {
  return typeof value === "boolean" ? value : fallback;
}

function number(value: unknown, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function toSlide(sectionId: string, item: ConfigRecord, index: number): StorefrontSlide {
  return {
    id: text(item.id, `${sectionId}::slide::${index}`),
    title: text(item.title),
    subtitle: text(item.subtitle),
    ctaLabel: text(item.ctaLabel ?? item.cta_label, "تسوّقي الآن"),
    imageUrl: text(item.imageUrl ?? item.image_url ?? item.url),
    storageKey: text(item.storageKey ?? item.storage_key),
    isActive: bool(item.isActive ?? item.is_active),
    sortOrder: number(item.sortOrder ?? item.sort_order, index),
  };
}

function toCircle(sectionId: string, item: ConfigRecord, index: number): StorefrontCircle {
  return {
    id: text(item.id, `${sectionId}::circle::${index}`),
    title: text(item.title),
    targetCategory: text(item.targetCategory ?? item.target_category),
    imageUrl: text(item.imageUrl ?? item.image_url ?? item.url),
    storageKey: text(item.storageKey ?? item.storage_key),
    isActive: bool(item.isActive ?? item.is_active),
    sortOrder: number(item.sortOrder ?? item.sort_order, index),
  };
}

function toTab(section: RawSection): StorefrontTab {
  const id = text(section.id);
  const config = asRecord(section.config);
  const slides = asArray(config.slides).map((item, index) => toSlide(id, item, index));
  const circles = asArray(config.circles ?? config.categories ?? config.collections).map((item, index) => toCircle(id, item, index));
  if (!slides.length && ["hero", "banner"].includes(text(section.section_type ?? section.type).toLowerCase())) {
    slides.push(toSlide(id, config, 0));
  }
  const promoConfig = asRecord(config.promo);
  const promo: StorefrontPromo = { flashTitle: text(promoConfig.flashTitle, "تخفيضات سريعة"), flashSubtitle: text(promoConfig.flashSubtitle, "عرض المزيد"), flashMode: text(promoConfig.flashMode, "flash"), freeShippingTitle: text(promoConfig.freeShippingTitle, "شحن مجاني"), freeShippingSubtitle: text(promoConfig.freeShippingSubtitle, "أضيفي المزيد للحصول عليه"), freeShippingCategory: text(promoConfig.freeShippingCategory) };
  return {
    id,
    title: text(section.title, "الرئيسية"),
    searchPlaceholder: text(config.searchPlaceholder ?? config.search_placeholder, "ابحثي عن منتج أو متجر"),
    isActive: bool(section.is_visible),
    sortOrder: number(section.sort_order),
    slides: slides.sort((a, b) => a.sortOrder - b.sortOrder),
    circles: circles.sort((a, b) => a.sortOrder - b.sortOrder),
    promo,
  };
}

function extractSections(response: SectionsResponse): RawSection[] {
  if (Array.isArray(response)) return response;
  return response.results ?? response.data ?? [];
}

async function fetchSections(endpoint: string) {
  const response = await apiCall<SectionsResponse>(endpoint);
  return extractSections(response);
}

async function fetchTabs(endpoint: string) {
  const sections = await fetchSections(endpoint);
  return sections.sort((a, b) => number(a.sort_order) - number(b.sort_order)).map(toTab);
}

async function fetchSection(id: string) {
  return apiCall<RawSection>(`/api/storefront-sections/${encodeURIComponent(id)}/`);
}

async function saveSection(id: string, changes: { title?: string; sort_order?: number; is_visible?: boolean; config?: ConfigRecord }) {
  await apiCall<RawSection>(`/api/storefront-sections/${encodeURIComponent(id)}/`, {
    method: "PATCH",
    body: JSON.stringify(changes),
  });
  return { tabs: await getAdminStorefront() };
}

function configWithItems(section: RawSection, key: "slides" | "circles", items: ConfigRecord[]) {
  return { ...asRecord(section.config), [key]: items };
}

function splitVisualId(id: string) {
  const match = id.match(/^(.+?)::(slide|circle)::(.+)$/);
  return match ? { sectionId: match[1], kind: match[2] as "slide" | "circle", itemId: match[3] } : undefined;
}

async function updateVisual(id: string, kind: "slide" | "circle", changes: Partial<StorefrontSlide | StorefrontCircle>) {
  const parsed = splitVisualId(id);
  if (!parsed || parsed.kind !== kind) throw new Error("معرّف العنصر غير صالح");
  const section = await fetchSection(parsed.sectionId);
  const config = asRecord(section.config);
  const key = kind === "slide" ? "slides" : "circles";
  const items = asArray(config[key]);
  const index = items.findIndex((item, itemIndex) => text(item.id, `${parsed.sectionId}::${kind}::${itemIndex}`) === id || text(item.id) === parsed.itemId);
  if (index < 0) throw new Error("العنصر غير موجود");
  items[index] = { ...items[index], ...changes } as ConfigRecord;
  return saveSection(parsed.sectionId, { config: configWithItems(section, key, items) });
}

async function deleteVisual(id: string, kind: "slide" | "circle") {
  const parsed = splitVisualId(id);
  if (!parsed || parsed.kind !== kind) throw new Error("معرّف العنصر غير صالح");
  const section = await fetchSection(parsed.sectionId);
  const config = asRecord(section.config);
  const key = kind === "slide" ? "slides" : "circles";
  const items = asArray(config[key]).filter((item, itemIndex) => text(item.id, `${parsed.sectionId}::${kind}::${itemIndex}`) !== id && text(item.id) !== parsed.itemId);
  return saveSection(parsed.sectionId, { config: configWithItems(section, key, items) });
}

export async function getStorefront() {
  const response = await apiCall<{ data?: RawSection[] }>("/api/home/");
  return (response.data ?? []).map(toTab).filter((tab) => tab.isActive);
}

export async function getAdminStorefront() {
  return fetchTabs("/api/storefront-sections/");
}

export async function createTab(payload: { title: string; searchPlaceholder: string }) {
  await apiCall<RawSection>("/api/storefront-sections/", {
    method: "POST",
    body: JSON.stringify({
      title: payload.title,
      section_type: "tab",
      config: { searchPlaceholder: payload.searchPlaceholder, slides: [], circles: [] },
      sort_order: Date.now(),
      is_visible: true,
    }),
  });
  return { tabs: await getAdminStorefront() };
}

export async function updatePromos(id: string, promo: StorefrontPromo) {
  const section = await fetchSection(id);
  const config = { ...asRecord(section.config), promo };
  return saveSection(id, { config });
}

export async function updateTab(id: string, payload: Partial<{ title: string; searchPlaceholder: string; isActive: boolean; sortOrder: number }>) {
  const section = await fetchSection(id);
  const config = { ...asRecord(section.config) };
  if (payload.searchPlaceholder !== undefined) config.searchPlaceholder = payload.searchPlaceholder;
  return saveSection(id, {
    title: payload.title,
    sort_order: payload.sortOrder,
    is_visible: payload.isActive,
    config,
  });
}

export async function deleteTab(id: string) {
  await apiCall(`/api/storefront-sections/${encodeURIComponent(id)}/`, { method: "DELETE" });
  return { tabs: await getAdminStorefront() };
}

export async function createSlide(tabId: string, payload: { title: string; subtitle: string; ctaLabel: string; image: ImagePayload }) {
  const section = await fetchSection(tabId);
  const config = asRecord(section.config);
  const slides = asArray(config.slides);
  slides.push({
    id: `${tabId}::slide::${Date.now()}`,
    title: payload.title,
    subtitle: payload.subtitle,
    ctaLabel: payload.ctaLabel,
    imageUrl: payload.image.dataUrl,
    fileName: payload.image.fileName,
    isActive: true,
    sortOrder: slides.length,
  });
  return saveSection(tabId, { config: configWithItems(section, "slides", slides) });
}

export async function updateSlide(id: string, payload: Partial<{ isActive: boolean; sortOrder: number }>) {
  return updateVisual(id, "slide", payload);
}

export async function deleteSlide(id: string) {
  return deleteVisual(id, "slide");
}

export async function createCircle(tabId: string, payload: { title: string; targetCategory: string; image?: ImagePayload }) {
  const section = await fetchSection(tabId);
  const config = asRecord(section.config);
  const circles = asArray(config.circles);
  circles.push({
    id: `${tabId}::circle::${Date.now()}`,
    title: payload.title,
    targetCategory: payload.targetCategory,
    imageUrl: payload.image?.dataUrl ?? "",
    fileName: payload.image?.fileName ?? "",
    isActive: true,
    sortOrder: circles.length,
  });
  return saveSection(tabId, { config: configWithItems(section, "circles", circles) });
}

export async function updateCircle(id: string, payload: Partial<{ isActive: boolean; sortOrder: number }>) {
  return updateVisual(id, "circle", payload);
}

export async function deleteCircle(id: string) {
  return deleteVisual(id, "circle");
}
