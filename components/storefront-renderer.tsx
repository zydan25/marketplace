import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import * as Linking from "expo-linking";
import { router } from "expo-router";
import { useMemo, useState } from "react";
import { Dimensions, Image, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { ProductCard } from "@/components/product-card";
import { formatYER } from "@/lib/catalog";
import type { StoreProduct } from "@/lib/product-api";
import type { StorefrontTheme } from "@/lib/storefront-api";

export type DynamicSection = {
  id: string | number;
  key?: string;
  type: string;
  title?: string;
  sort_order?: number;
  is_visible?: boolean;
  config?: Record<string, any>;
};

type RendererProps = {
  sections: DynamicSection[];
  theme: StorefrontTheme | null;
  products: StoreProduct[];
  categories: Array<{ id: number; name: string; slug?: string; imageUrl?: string }>;
};

const width = Dimensions.get("window").width;

export function StorefrontRenderer({ sections, theme, products, categories }: RendererProps) {
  const layout = theme?.layout ?? {};
  const tokens = theme?.tokens ?? {};
  const family = String(layout.family ?? "fashion");
  const primary = String(tokens.primary ?? (family === "electronics" ? "#0D47A1" : "#E60023"));
  const background = String(tokens.background ?? "#FFF");
  const sectionGap = Number(layout.section_gap ?? 10);
  const sorted = useMemo(() => [...sections].filter((section) => section.is_visible !== false).sort((a, b) => Number(a.sort_order ?? 0) - Number(b.sort_order ?? 0)), [sections]);

  return <View style={[styles.root, { backgroundColor: background }]}>{sorted.map((section) => <View key={String(section.id)} style={{ marginBottom: sectionGap }}><RenderSection section={section} theme={theme} products={products} categories={categories} primary={primary} family={family} /></View>)}</View>;
}

type SectionRendererProps = Omit<RendererProps, "sections"> & { section: DynamicSection; primary: string; family: string };

function RenderSection({ section, theme, products, categories, primary, family }: SectionRendererProps) {
  const config = section.config ?? {};
  const type = String(section.type ?? "").toLowerCase();
  switch (type) {
    case "header": return <Header config={config} categories={categories} primary={primary} family={family} />;
    case "hero":
    case "banner": return <Hero section={section} primary={primary} theme={theme} />;
    case "promo_strip": return <PromoStrip config={config} primary={primary} />;
    case "notice": return <Notice config={config} primary={primary} />;
    case "category_grid":
    case "category": return <CategoryGrid title={section.title} config={config} categories={categories} primary={primary} />;
    case "brand_grid": return <BrandGrid title={section.title} config={config} products={products} primary={primary} />;
    case "tabs":
    case "tab": return <BrowseTabs config={config} primary={primary} />;
    case "catalog_toolbar": return <CatalogToolbar title={section.title} config={config} itemsCount={products.length} primary={primary} />;
    case "product_grid":
    case "trend": return <ProductGrid section={section} products={products} primary={primary} theme={theme} />;
    case "bottom_nav": return <BottomNav config={config} primary={primary} />;
    default: return null;
  }
}

function Header({ config, categories, primary, family }: { config: Record<string, any>; categories: RendererProps["categories"]; primary: string; family: string }) {
  const chips = categories.slice(0, Number(config.category_chip_limit ?? 6));
  const [query] = useState("");
  if (family === "electronics") return <View style={[styles.electronicsHeader, { backgroundColor: primary }]}><View style={styles.electronicsTop}>{config.show_notifications !== false ? <IconButton name="notifications-none" /> : null}<View style={styles.searchSolid}><Text style={styles.searchPlaceholder}>{query}</Text><MaterialIcons name="search" size={21} color="#123B72" /></View>{config.show_account !== false ? <IconButton name="account-circle" /> : null}</View>{config.show_category_nav !== false ? <ScrollView horizontal inverted showsHorizontalScrollIndicator={false} contentContainerStyle={styles.blueChips}>{chips.map((item) => <Pressable key={item.id} onPress={() => router.push(`/collection?category=${encodeURIComponent(item.slug ?? item.name)}` as never)} style={styles.blueChip}><Text style={styles.blueChipText}>{item.name}</Text></Pressable>)}</ScrollView> : null}</View>;
  return <View style={styles.fashionHeader}><View style={styles.fashionTop}>{config.show_favorites !== false ? <IconButton name="favorite-border" badge="3" /> : null}<View style={styles.searchFloating}><Text style={[styles.searchPlaceholder, { flex: 1 }]}>ابحث عن منتج أو متجر</Text><MaterialIcons name="search" size={20} color="#111" /></View>{config.show_notifications !== false ? <IconButton name="mail-outline" /> : null}{config.show_calendar !== false ? <IconButton name="calendar-today" /> : null}</View>{config.show_category_chips !== false ? <ScrollView horizontal inverted showsHorizontalScrollIndicator={false} contentContainerStyle={styles.fashionChips}>{chips.map((item) => <Pressable key={item.id} onPress={() => router.push(`/collection?category=${encodeURIComponent(item.slug ?? item.name)}` as never)}><Text style={[styles.fashionChipText, { color: primary }]}>{item.name}</Text></Pressable>)}</ScrollView> : null}</View>;
}

function IconButton({ name, badge }: { name: any; badge?: string }) { return <View style={styles.iconButton}><MaterialIcons name={name} size={22} color="#111" />{badge ? <View style={styles.badgeDot}><Text style={styles.badgeText}>{badge}</Text></View> : null}</View>; }

function Hero({ section, primary, theme }: { section: DynamicSection; primary: string; theme: StorefrontTheme | null }) {
  const slides = Array.isArray(section.config?.slides) ? section.config!.slides.filter((x: any) => x?.visible !== false && x?.isActive !== false) : [];
  const [index, setIndex] = useState(0);
  const slide = slides[Math.min(index, Math.max(0, slides.length - 1))] ?? slides[0];
  const height = Number(section.config?.height ?? theme?.layout?.hero_height ?? 260);
  if (!slide) return null;
  const image = String(slide.imageUrl ?? slide.image_url ?? "");
  return <View><Pressable style={[styles.hero, { height }]} onPress={() => navigateUrl(String(slide.url ?? ""))}>{image ? <Image source={{ uri: image }} style={StyleSheet.absoluteFillObject} resizeMode="cover" /> : <View style={styles.heroEmpty}><MaterialIcons name="image" size={42} color="#AAA" /><Text style={styles.heroEmptyText}>أضف البانر من محرر التصميم</Text></View>}<View style={styles.heroShade} /><View style={styles.heroText}>{slide.badge ? <Text style={styles.heroBadge}>{slide.badge}</Text> : null}{slide.title ? <Text style={styles.heroTitle}>{slide.title}</Text> : null}{slide.subtitle ? <Text style={styles.heroSubtitle}>{slide.subtitle}</Text> : null}{slide.ctaLabel ? <View style={[styles.heroButton, { borderColor: primary }]}><Text style={styles.heroButtonText}>{slide.ctaLabel}</Text><MaterialIcons name="arrow-back" size={16} color="#111" /></View> : null}</View></Pressable>{slides.length > 1 ? <View style={styles.dots}>{slides.map((item: any, i: number) => <Pressable key={String(item.id ?? i)} onPress={() => setIndex(i)} style={[styles.dot, { backgroundColor: i === index ? primary : "#D0D0D0" }]} />)}</View> : null}</View>;
}

function PromoStrip({ config, primary }: { config: Record<string, any>; primary: string }) { const items = Array.isArray(config.items) ? config.items : []; return <View style={styles.promoStrip}>{items.map((item: any, index: number) => <View key={String(item.id ?? index)} style={[styles.promoItem, index < items.length - 1 && styles.promoDivider]}><Text style={styles.promoTitle}>{String(item.title ?? "")}</Text><Text style={[styles.promoValue, { color: primary }]}>{String(item.value ?? "")}</Text>{item.note ? <Text style={styles.promoNote}>{String(item.note)}</Text> : null}</View>)}</View>; }
function Notice({ config, primary }: { config: Record<string, any>; primary: string }) { return <View style={styles.notice}><View style={[styles.noticeLine, { backgroundColor: primary }]} /><Text style={styles.noticeText}>{String(config.text ?? "")}</Text></View>; }
function CategoryGrid({ title, config, categories, primary }: { title?: string; config: Record<string, any>; categories: RendererProps["categories"]; primary: string }) { const columns = Math.max(1, Number(config.columns ?? 4)); const rows = Math.max(1, Number(config.rows ?? 3)); const size = Math.max(42, Number(config.size ?? 72)); const gap = Math.max(4, Number(config.gap ?? 10)); const items = categories.slice(0, rows * columns); return <View style={styles.sectionCard}>{title ? <SectionTitle title={title} primary={primary} /> : null}<View style={[styles.categoryGrid, { columnGap: gap, rowGap: gap }]}>{items.map((category) => <Pressable key={category.id} style={{ width: `${100 / columns}%` }} onPress={() => router.push(`/collection?category=${encodeURIComponent(category.slug ?? category.name)}` as never)}><View style={[styles.categoryVisual, { width: size, height: size, borderRadius: String(config.shape ?? "circle") === "circle" ? size / 2 : Number(config.radius ?? 14), alignSelf: "center" }]}>{category.imageUrl ? <Image source={{ uri: category.imageUrl }} style={StyleSheet.absoluteFillObject} resizeMode="cover" /> : <MaterialIcons name="category" size={Math.round(size * 0.34)} color={primary} />}</View><Text numberOfLines={Number(config.label_lines ?? 1)} style={styles.categoryLabel}>{category.name}</Text></Pressable>)}</View></View>; }
function BrandGrid({ title, config, products, primary }: { title?: string; config: Record<string, any>; products: StoreProduct[]; primary: string }) { const limit = Math.max(1, Number(config.limit ?? 8)); const size = Math.max(48, Number(config.size ?? 82)); const seen = new Set<string>(); const brands: Array<{ name: string; image: string }> = []; for (const product of products) { const name = (product as any).brand?.trim(); if (!name || seen.has(name)) continue; seen.add(name); brands.push({ name, image: product.images[0]?.url ?? "" }); if (brands.length >= limit) break; } const columns = Math.max(1, Number(config.columns ?? 4)); return <View style={styles.sectionCard}>{title ? <SectionTitle title={title} primary={primary} /> : null}<View style={[styles.categoryGrid, { columnGap: Number(config.gap ?? 12), rowGap: Number(config.gap ?? 12) }]}>{brands.map((brand) => <Pressable key={brand.name} style={{ width: `${100 / columns}%` }} onPress={() => router.push(`/collection?brand=${encodeURIComponent(brand.name)}` as never)}><View style={[styles.brandVisual, { width: size, height: size, borderRadius: size / 2, borderColor: `${primary}35` }]}>{brand.image ? <Image source={{ uri: brand.image }} style={StyleSheet.absoluteFillObject} resizeMode="cover" /> : <MaterialIcons name="store" size={28} color={primary} />}</View><Text style={styles.brandLabel}>{brand.name}</Text></Pressable>)}</View></View>; }
function BrowseTabs({ config, primary }: { config: Record<string, any>; primary: string }) { const tabs = Array.isArray(config.tabs) ? config.tabs : Array.isArray(config.items) ? config.items : []; return <ScrollView horizontal inverted showsHorizontalScrollIndicator={false} contentContainerStyle={styles.browseTabs}>{tabs.map((item: any, index: number) => <Pressable key={String(item.id ?? index)} onPress={() => navigateUrl(String(item.url ?? ""))} style={[styles.browseTab, index === tabs.length - 1 && { backgroundColor: primary }]}><Text style={[styles.browseTabText, index === tabs.length - 1 && { color: "#FFF" }]}>{String(item.title ?? "")}</Text></Pressable>)}</ScrollView>; }
function CatalogToolbar({ title, config, itemsCount, primary }: { title?: string; config: Record<string, any>; itemsCount: number; primary: string }) { return <View style={styles.toolbar}><View style={styles.toolbarTitleWrap}>{config.show_count !== false ? <Text style={styles.count}>{itemsCount} قطعة</Text> : null}{title ? <Text style={styles.toolbarTitle}>{title}</Text> : null}</View><View style={styles.toolbarActions}>{config.show_sort !== false ? <View style={styles.toolbarButton}><MaterialIcons name="sort" size={16} color={primary} /><Text style={styles.toolbarText}>الترتيب</Text></View> : null}{config.show_filter !== false ? <View style={styles.toolbarButton}><MaterialIcons name="tune" size={16} color={primary} /><Text style={styles.toolbarText}>تصفية</Text></View> : null}</View></View>; }
function ProductGrid({ section, products, primary, theme }: { section: DynamicSection; products: StoreProduct[]; primary: string; theme: StorefrontTheme | null }) { const c = section.config ?? {}; const cols = Math.max(1, Number(c.columns_mobile ?? theme?.layout?.product_columns_mobile ?? 2)); const rows = Math.max(1, Number(c.rows ?? 4)); const limit = Math.max(1, Number(c.limit ?? rows * cols)); const source = String(c.source ?? "latest").toLowerCase(); const filtered = products.filter((product) => source === "discounts" || source === "deals" ? product.discountPercent > 0 : source === "trending" || source === "trend" ? product.isTrending : true).slice(0, limit); const gap = Math.max(4, Number(c.gap ?? theme?.layout?.product_gap ?? 10)); return <View style={styles.productsSection}><View style={styles.sectionTitleRow}><Text style={styles.sectionTitle}>{section.title || (source === "discounts" ? "المعروضات والتخفيضات" : "منتجات مختارة")}</Text>{c.show_see_all !== false ? <Pressable onPress={() => router.push("/collection" as never)}><Text style={[styles.seeAll, { color: primary }]}>عرض الكل</Text></Pressable> : null}</View><View style={styles.productGrid}>{filtered.map((product) => <View key={product.id} style={{ width: `${100 / cols}%`, paddingHorizontal: gap / 2, marginBottom: gap }}><ProductCard product={product} />{source === "discounts" && product.discountPercent > 0 ? <Text style={[styles.discountLine, { color: primary }]}>خصم {product.discountPercent}%</Text> : null}</View>)}</View></View>; }
function BottomNav({ config, primary }: { config: Record<string, any>; primary: string }) { const items = Array.isArray(config.items) && config.items.length ? config.items : [{ label: "حسابي", icon: "person-outline", url: "/settings" }, { label: "المفضلة", icon: "favorite-border", url: "/favorites" }, { label: "السلة", icon: "shopping-cart", url: "/checkout" }, { label: "المنتجات", icon: "inventory-2", url: "/collection" }, { label: "الرئيسية", icon: "home", url: "/" }]; return <View style={styles.bottomNav}>{items.map((item: any, index: number) => <Pressable key={`${String(item.label)}-${index}`} style={[styles.bottomItem, index === items.length - 1 && styles.bottomActive]} onPress={() => navigateUrl(String(item.url ?? ""))}><MaterialIcons name={item.icon || "circle"} size={22} color={index === items.length - 1 ? primary : "#607080"} /><Text style={[styles.bottomText, index === items.length - 1 && { color: primary }]}>{String(item.label ?? "")}</Text></Pressable>)}</View>; }
function SectionTitle({ title, primary }: { title: string; primary: string }) { return <View style={styles.sectionTitleRow}><Text style={styles.sectionTitle}>{title}</Text><View style={[styles.titleAccent, { backgroundColor: primary }]} /></View>; }
function navigateUrl(url: string) { const value = String(url ?? "").trim(); if (!value) return; if (value.startsWith("/")) router.push(value as never); else if (/^https?:\/\//i.test(value)) void Linking.openURL(value); }

const styles = StyleSheet.create({
  root: { flex: 1 },
  sectionCard: { backgroundColor: "#FFF", padding: 12 },
  sectionTitleRow: { flexDirection: "row-reverse", alignItems: "center", justifyContent: "space-between", marginBottom: 10, paddingHorizontal: 6 },
  sectionTitle: { fontSize: 17, fontWeight: "900", color: "#151515", textAlign: "right" },
  titleAccent: { width: 26, height: 4, borderRadius: 3 },
  fashionHeader: { backgroundColor: "transparent", paddingTop: 5, paddingHorizontal: 10 },
  fashionTop: { flexDirection: "row-reverse", alignItems: "center", gap: 8 },
  searchFloating: { flex: 1, height: 46, backgroundColor: "#FFF", borderRadius: 13, flexDirection: "row-reverse", alignItems: "center", paddingHorizontal: 12, borderWidth: 1, borderColor: "#E9E9E9" },
  searchSolid: { flex: 1, height: 42, backgroundColor: "#FFF", borderRadius: 0, flexDirection: "row-reverse", alignItems: "center", paddingHorizontal: 12 },
  searchPlaceholder: { fontSize: 11, textAlign: "right", color: "#222" },
  iconButton: { width: 36, height: 36, borderRadius: 18, backgroundColor: "#FFF", alignItems: "center", justifyContent: "center", position: "relative", borderWidth: 1, borderColor: "#EEE" },
  badgeDot: { position: "absolute", top: -2, right: -2, minWidth: 15, height: 15, borderRadius: 9, backgroundColor: "#E60023", alignItems: "center", justifyContent: "center" },
  badgeText: { color: "#FFF", fontSize: 8, fontWeight: "900" },
  fashionChips: { paddingHorizontal: 8, paddingVertical: 8, gap: 15 },
  fashionChipText: { fontSize: 11, fontWeight: "800" },
  electronicsHeader: { paddingTop: 10, paddingBottom: 8 },
  electronicsTop: { flexDirection: "row", alignItems: "center", gap: 7, paddingHorizontal: 8 },
  blueChips: { paddingHorizontal: 10, paddingTop: 8, gap: 17 },
  blueChip: { paddingHorizontal: 3, paddingVertical: 5 },
  blueChipText: { color: "#FFF", fontSize: 11, fontWeight: "900" },
  hero: { marginHorizontal: width > 700 ? 12 : 0, marginTop: 3, borderRadius: width > 700 ? 16 : 0, overflow: "hidden", backgroundColor: "#EEE", position: "relative" },
  heroShade: { ...StyleSheet.absoluteFillObject, backgroundColor: "rgba(0,0,0,0.25)" },
  heroText: { position: "absolute", right: 18, bottom: 18, maxWidth: "78%", alignItems: "flex-end" },
  heroBadge: { backgroundColor: "#FFF", color: "#111", fontSize: 10, fontWeight: "800", paddingHorizontal: 8, paddingVertical: 4, borderRadius: 99 },
  heroTitle: { color: "#FFF", fontSize: 24, fontWeight: "900", marginTop: 7, textAlign: "right" },
  heroSubtitle: { color: "#FFF", fontSize: 12, marginTop: 3, textAlign: "right" },
  heroButton: { marginTop: 9, backgroundColor: "#FFF", borderWidth: 1, borderRadius: 20, paddingHorizontal: 13, paddingVertical: 8, flexDirection: "row-reverse", gap: 5, alignItems: "center" },
  heroButtonText: { fontSize: 10, fontWeight: "900", color: "#111" },
  heroEmpty: { flex: 1, alignItems: "center", justifyContent: "center" },
  heroEmptyText: { color: "#888", marginTop: 5, fontSize: 10 },
  dots: { flexDirection: "row", justifyContent: "center", gap: 6, paddingVertical: 6 },
  dot: { width: 7, height: 7, borderRadius: 4 },
  promoStrip: { backgroundColor: "#FFF8F8", borderTopWidth: 1, borderBottomWidth: 1, borderColor: "#F0DDDD", flexDirection: "row-reverse", paddingVertical: 8 },
  promoItem: { flex: 1, alignItems: "center", paddingHorizontal: 5 },
  promoDivider: { borderLeftWidth: 1, borderLeftColor: "#F0DDDD" },
  promoTitle: { fontSize: 9, color: "#666", textAlign: "center" },
  promoValue: { fontSize: 14, fontWeight: "900", marginTop: 2 },
  promoNote: { fontSize: 8, color: "#888", marginTop: 2 },
  notice: { backgroundColor: "#FFFDF2", minHeight: 52, alignItems: "center", justifyContent: "center", paddingHorizontal: 12, flexDirection: "row-reverse", gap: 7 },
  noticeLine: { width: 5, height: 28, borderRadius: 3 },
  noticeText: { flex: 1, fontSize: 13, lineHeight: 21, color: "#222", textAlign: "center" },
  categoryGrid: { flexDirection: "row-reverse", flexWrap: "wrap", alignItems: "flex-start" },
  categoryVisual: { backgroundColor: "#F4F4F4", overflow: "hidden", alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: "#EEE" },
  categoryLabel: { fontSize: 9, fontWeight: "800", color: "#333", textAlign: "center", marginTop: 5 },
  brandVisual: { backgroundColor: "#FFF", overflow: "hidden", alignItems: "center", justifyContent: "center", borderWidth: 2 },
  brandLabel: { fontSize: 9, fontWeight: "800", color: "#333", textAlign: "center", marginTop: 5 },
  browseTabs: { paddingHorizontal: 10, gap: 8 },
  browseTab: { backgroundColor: "#F3F5F7", borderRadius: 18, paddingHorizontal: 13, paddingVertical: 8 },
  browseTabText: { color: "#333", fontSize: 10, fontWeight: "900" },
  toolbar: { backgroundColor: "#FFF", borderTopWidth: 1, borderBottomWidth: 1, borderColor: "#EAEAEA", padding: 9, flexDirection: "row-reverse", alignItems: "center", justifyContent: "space-between" },
  toolbarTitleWrap: { alignItems: "flex-end" },
  toolbarTitle: { fontSize: 15, fontWeight: "900", color: "#111" },
  count: { fontSize: 9, color: "#888", marginBottom: 2 },
  toolbarActions: { flexDirection: "row-reverse", gap: 6 },
  toolbarButton: { flexDirection: "row-reverse", alignItems: "center", gap: 4, backgroundColor: "#F4F6F8", borderRadius: 9, paddingHorizontal: 8, paddingVertical: 6 },
  toolbarText: { fontSize: 8, fontWeight: "800", color: "#333" },
  productsSection: { backgroundColor: "#FFF", paddingHorizontal: 4, paddingTop: 8 },
  productGrid: { flexDirection: "row-reverse", flexWrap: "wrap", marginHorizontal: -2 },
  seeAll: { fontSize: 10, fontWeight: "900" },
  discountLine: { fontSize: 9, fontWeight: "900", textAlign: "right", paddingHorizontal: 5 },
  bottomNav: { minHeight: 64, backgroundColor: "#FFF", borderTopWidth: 1, borderColor: "#E7E7E7", flexDirection: "row-reverse", alignItems: "stretch", paddingHorizontal: 5 },
  bottomItem: { flex: 1, alignItems: "center", justifyContent: "center", gap: 2 },
  bottomActive: { borderTopWidth: 3, borderTopColor: "#E60023" },
  bottomText: { fontSize: 9, fontWeight: "800", color: "#607080" },
});
