import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import * as Linking from "expo-linking";
import { router } from "expo-router";
import { useCallback, useMemo, useState } from "react";
import { Dimensions, FlatList, Image, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";

import { ProductCard } from "@/components/product-card";
import { ShopHeader } from "@/components/shop-header";
import { useCategories } from "@/hooks/use-categories";
import { useProducts } from "@/hooks/use-products";
import { useStorefront } from "@/hooks/use-storefront";
import type { StoreProduct } from "@/lib/product-api";
import type { StorefrontCard, StorefrontCircle, StorefrontSlide, StorefrontTab } from "@/lib/storefront-api";

const screenWidth = Dimensions.get("window").width;
const contentWidth = Math.min(screenWidth, 1180);

type StorefrontSectionConfig = Record<string, unknown>;

export default function StoreScreen() {
  const { products, loading: productsLoading, refresh: refreshProducts } = useProducts();
  const { tabs: sections, loading: storefrontLoading, refresh: refreshStorefront } = useStorefront();
  const { categories, loading: categoriesLoading, refresh: refreshCategories } = useCategories();
  const [refreshing, setRefreshing] = useState(false);

  const visibleSections = useMemo(
    () => sections.filter((section) => section.isActive).sort((a, b) => a.sortOrder - b.sortOrder),
    [sections],
  );

  const globalSearchPlaceholder = useMemo(
    () => visibleSections.find((section) => section.searchPlaceholder)?.searchPlaceholder ?? "ابحثي عن منتج أو متجر",
    [visibleSections],
  );

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await Promise.all([refreshProducts(), refreshStorefront(), refreshCategories()]);
    } finally {
      setRefreshing(false);
    }
  }, [refreshCategories, refreshProducts, refreshStorefront]);

  const renderedSections = visibleSections.length > 0 ? visibleSections : fallbackSections(products, categories);

  return (
    <View style={styles.page}>
      <ShopHeader placeholder={globalSearchPlaceholder} />
      <FlatList
        data={products}
        keyExtractor={(item) => item.id}
        numColumns={2}
        style={styles.list}
        contentContainerStyle={styles.listContent}
        columnWrapperStyle={styles.productRow}
        showsVerticalScrollIndicator
        refreshControl={
          <RefreshControl
            refreshing={refreshing || productsLoading || storefrontLoading || categoriesLoading}
            onRefresh={refresh}
          />
        }
        ListHeaderComponent={
          <View style={styles.headerContent}>
            {renderedSections.map((section) => (
              <StorefrontSection key={String(section.id)} section={section} products={products} />
            ))}
          </View>
        }
        renderItem={({ item }) => <View style={styles.productCell}><ProductCard product={item} /></View>}
        ListEmptyComponent={<EmptyState loading={productsLoading || storefrontLoading} />}
      />
    </View>
  );
}

function fallbackSections(products: StoreProduct[], categories: { name: string }[]): StorefrontTab[] {
  const firstImage = products[0]?.images[0]?.url ?? "";
  return [{
    id: "fallback",
    type: "hero",
    title: "الرئيسية",
    searchPlaceholder: "ابحثي عن منتج أو متجر",
    isActive: true,
    sortOrder: 0,
    slides: firstImage
      ? [{ id: "hero", title: "اختيارات مميزة", subtitle: "تسوّقي أحدث المنتجات", imageUrl: firstImage, url: "/collection", badge: "", visible: true, sortOrder: 0, ctaLabel: "تسوّقي الآن" }]
      : [],
    circles: categories.slice(0, 12).map((category, index) => ({
      id: String(index),
      title: category.name,
      targetCategory: category.name,
      imageUrl: "",
      url: `/collection?category=${encodeURIComponent(category.name)}`,
      visible: true,
      sortOrder: index,
    })),
    cards: [],
    actions: [],
    promo: { enabled: false, flashTitle: "", flashSubtitle: "", flashMode: "", freeShippingTitle: "", freeShippingSubtitle: "", freeShippingCategory: "" },
    config: { showGlobalGrid: true },
  }];
}

function StorefrontSection({ section, products }: { section: StorefrontTab; products: StoreProduct[] }) {
  const config = (section.config ?? {}) as StorefrontSectionConfig;
  const filtered = filterProducts(products, config);
  const sectionType = section.type.toLowerCase();

  return (
    <View style={styles.section}>
      {(sectionType === "hero" || sectionType === "banner" || section.slides.length > 0) && section.slides.length > 0 && (
        <HeroBlock slides={section.slides} />
      )}
      {(sectionType === "category" || section.circles.length > 0) && section.circles.length > 0 && (
        <CircleBlock circles={section.circles} />
      )}
      {(sectionType === "trend" || section.cards.length > 0) && section.cards.length > 0 && (
        <CardsBlock cards={section.cards} />
      )}
      {section.promo?.enabled && <PromoBlock promo={section.promo} />}
      {section.actions.length > 0 && <ActionBlock actions={section.actions} />}
      {(sectionType === "product_grid" || config.showProducts === true || config.showGlobalGrid === true) && (
        <ProductStrip title={section.title} items={filtered} mode={String(config.cardMode ?? "horizontal")} />
      )}
    </View>
  );
}

function HeroBlock({ slides }: { slides: StorefrontSlide[] }) {
  const slide = slides.find((item) => item.visible !== false) ?? slides[0];
  if (!slide?.imageUrl) return null;
  return (
    <Pressable style={styles.hero} onPress={() => navigateUrl(slide.url)} accessibilityRole="button">
      <Image source={{ uri: slide.imageUrl }} style={styles.heroImage} resizeMode="cover" />
      <View style={styles.heroShade} />
      <View style={styles.heroText}>
        {slide.badge ? <Text style={styles.badge}>{slide.badge}</Text> : null}
        <Text style={styles.heroTitle}>{slide.title}</Text>
        {slide.subtitle ? <Text style={styles.heroSubtitle}>{slide.subtitle}</Text> : null}
        {slide.ctaLabel ? (
          <View style={styles.heroButton}>
            <Text style={styles.heroButtonText}>{slide.ctaLabel}</Text>
            <MaterialIcons name="arrow-back" size={16} color="#111" />
          </View>
        ) : null}
      </View>
    </Pressable>
  );
}

function CircleBlock({ circles }: { circles: StorefrontCircle[] }) {
  const visible = circles.filter((circle) => circle.visible !== false);
  if (!visible.length) return null;
  return (
    <View style={styles.circleArea}>
      <ScrollView horizontal inverted showsHorizontalScrollIndicator={false} contentContainerStyle={styles.circleScroller}>
        {visible.map((circle) => (
          <Pressable
            key={circle.id}
            style={styles.circleItem}
            onPress={() => navigateUrl(circle.url || `/collection?category=${encodeURIComponent(circle.targetCategory || circle.title)}`)}
          >
            <View style={styles.circleImage}>
              {circle.imageUrl ? <Image source={{ uri: circle.imageUrl }} style={StyleSheet.absoluteFillObject} /> : <MaterialIcons name="category" size={24} color="#777" />}
            </View>
            <Text numberOfLines={1} style={styles.circleText}>{circle.title}</Text>
          </Pressable>
        ))}
      </ScrollView>
    </View>
  );
}

function CardsBlock({ cards }: { cards: StorefrontCard[] }) {
  const visible = cards.filter((card) => card.visible !== false);
  if (!visible.length) return null;
  return (
    <View style={styles.cardsWrap}>
      <ScrollView horizontal inverted showsHorizontalScrollIndicator={false} contentContainerStyle={styles.cardsScroller}>
        {visible.map((card) => (
          <Pressable key={card.id} style={styles.contentCard} onPress={() => navigateUrl(card.url)}>
            {card.imageUrl ? <Image source={{ uri: card.imageUrl }} style={styles.cardImage} /> : <View style={styles.cardImageFallback}><MaterialIcons name="image" size={28} color="#aaa" /></View>}
            <View style={styles.cardBody}>
              {card.badge ? <Text style={styles.cardBadge}>{card.badge}</Text> : null}
              <Text style={styles.cardTitle}>{card.title}</Text>
              {card.subtitle ? <Text numberOfLines={2} style={styles.cardSubtitle}>{card.subtitle}</Text> : null}
            </View>
          </Pressable>
        ))}
      </ScrollView>
    </View>
  );
}

function PromoBlock({ promo }: { promo: NonNullable<StorefrontTab["promo"]> }) {
  return (
    <View style={styles.promo}>
      <View style={styles.promoItem}><MaterialIcons name="bolt" size={19} color="#111" /><View><Text style={styles.promoTitle}>{promo.flashTitle}</Text><Text style={styles.promoSub}>{promo.flashSubtitle}</Text></View></View>
      <View style={styles.promoDivider} />
      <View style={styles.promoItem}><MaterialIcons name="local-shipping" size={19} color="#111" /><View><Text style={styles.promoTitle}>{promo.freeShippingTitle}</Text><Text style={styles.promoSub}>{promo.freeShippingSubtitle}</Text></View></View>
    </View>
  );
}

function ActionBlock({ actions }: { actions: { label: string; url: string; visible: boolean }[] }) {
  const visible = actions.filter((action) => action.visible !== false && action.label.trim());
  if (!visible.length) return null;
  return <View style={styles.actions}>{visible.map((action, index) => <Pressable key={`${action.label}-${index}`} style={styles.action} onPress={() => navigateUrl(action.url)}><Text style={styles.actionText}>{action.label}</Text><MaterialIcons name="arrow-back" size={16} color="#111" /></Pressable>)}</View>;
}

function ProductStrip({ title, items, mode }: { title: string; items: StoreProduct[]; mode: string }) {
  if (!items.length) return null;
  return (
    <View style={styles.productStrip}>
      <View style={styles.sectionHeader}><Text style={styles.sectionTitle}>{title}</Text><Pressable onPress={() => router.push("/collection" as never)}><Text style={styles.seeAll}>عرض الكل</Text></Pressable></View>
      <ScrollView horizontal inverted showsHorizontalScrollIndicator={false} contentContainerStyle={styles.productStripScroller}>
        {items.slice(0, 12).map((item) => <View key={item.id} style={[styles.stripProduct, mode === "compact" && styles.stripProductCompact]}><ProductCard product={item} /></View>)}
      </ScrollView>
    </View>
  );
}

function filterProducts(items: StoreProduct[], config: StorefrontSectionConfig) {
  const ids = Array.isArray(config.productIds) ? new Set(config.productIds.map(String)) : null;
  const category = typeof config.category === "string" ? config.category : "";
  const mode = String(config.mode ?? "");
  let result = items.filter((item) => !ids || ids.has(String(item.id))).filter((item) => !category || item.categories.includes(category));
  if (mode === "deals") result = result.filter((item) => item.discountPercent > 0);
  if (mode === "bestsellers") result = result.filter((item) => item.rating >= 4 || item.reviews > 0);
  return result;
}

function navigateUrl(url: string) {
  const value = url.trim();
  if (!value) return;
  if (value.startsWith("/")) {
    router.push(value as never);
    return;
  }
  if (/^https?:\/\//i.test(value)) void Linking.openURL(value);
}

function EmptyState({ loading }: { loading: boolean }) {
  return <View style={styles.empty}><MaterialIcons name="inventory-2" size={44} color="#aaa" /><Text style={styles.emptyTitle}>{loading ? "جارٍ تحميل المتجر" : "لا توجد منتجات متاحة"}</Text><Text style={styles.emptyText}>يمكن للإدارة التحكم بالأقسام والمنتجات من لوحة المنصة.</Text></View>;
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: "#fff" },
  list: { flex: 1 },
  listContent: { paddingBottom: 110 },
  headerContent: { width: "100%", maxWidth: contentWidth, alignSelf: "center" },
  section: { width: "100%" },
  hero: { marginHorizontal: screenWidth > 700 ? 16 : 0, marginTop: 12, borderRadius: screenWidth > 700 ? 18 : 0, overflow: "hidden", height: Math.min(460, Math.max(260, screenWidth * 0.68)), backgroundColor: "#f5f5f5", position: "relative" },
  heroImage: { width: "100%", height: "100%" },
  heroShade: { ...StyleSheet.absoluteFillObject, backgroundColor: "rgba(0,0,0,.25)" },
  heroText: { position: "absolute", right: 22, bottom: 22, maxWidth: "74%", alignItems: "flex-end" },
  badge: { backgroundColor: "#fff", color: "#111", fontSize: 10, fontWeight: "800", paddingHorizontal: 8, paddingVertical: 4, borderRadius: 99 },
  heroTitle: { color: "#fff", fontSize: screenWidth > 700 ? 31 : 25, fontWeight: "900", textAlign: "right", marginTop: 9 },
  heroSubtitle: { color: "#fff", fontSize: 13, textAlign: "right", marginTop: 5 },
  heroButton: { marginTop: 12, backgroundColor: "#fff", borderRadius: 22, paddingHorizontal: 14, paddingVertical: 10, flexDirection: "row-reverse", alignItems: "center", gap: 6 },
  heroButtonText: { color: "#111", fontSize: 12, fontWeight: "800" },
  circleArea: { paddingVertical: 18 },
  circleScroller: { paddingHorizontal: 16, gap: 18 },
  circleItem: { width: 68, alignItems: "center" },
  circleImage: { width: 62, height: 62, borderRadius: 31, backgroundColor: "#f4f4f4", overflow: "hidden", alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: "#eee" },
  circleText: { fontSize: 11, color: "#333", fontWeight: "700", marginTop: 7, maxWidth: 68, textAlign: "center" },
  cardsWrap: { paddingVertical: 6 },
  cardsScroller: { paddingHorizontal: 16, gap: 12 },
  contentCard: { width: 250, borderRadius: 16, overflow: "hidden", backgroundColor: "#fff", borderWidth: 1, borderColor: "#eee" },
  cardImage: { width: "100%", height: 145, backgroundColor: "#f5f5f5" },
  cardImageFallback: { width: "100%", height: 145, backgroundColor: "#f5f5f5", alignItems: "center", justifyContent: "center" },
  cardBody: { padding: 12, alignItems: "flex-end" },
  cardBadge: { fontSize: 10, color: "#8b5cf6", fontWeight: "800", marginBottom: 3 },
  cardTitle: { fontSize: 15, fontWeight: "900", color: "#111", textAlign: "right" },
  cardSubtitle: { fontSize: 11, color: "#777", lineHeight: 18, textAlign: "right", marginTop: 4 },
  promo: { marginHorizontal: 16, marginVertical: 10, borderRadius: 14, backgroundColor: "#faf7f1", paddingVertical: 13, paddingHorizontal: 12, flexDirection: "row-reverse", alignItems: "center" },
  promoItem: { flex: 1, flexDirection: "row-reverse", alignItems: "center", gap: 8 },
  promoDivider: { width: 1, height: 32, backgroundColor: "#e5e5e5", marginHorizontal: 8 },
  promoTitle: { fontSize: 11, fontWeight: "900", color: "#111", textAlign: "right" },
  promoSub: { fontSize: 10, color: "#777", marginTop: 2, textAlign: "right" },
  actions: { flexDirection: "row-reverse", flexWrap: "wrap", gap: 8, padding: 16 },
  action: { minHeight: 42, paddingHorizontal: 13, borderRadius: 21, borderWidth: 1, borderColor: "#ddd", flexDirection: "row-reverse", alignItems: "center", gap: 6 },
  actionText: { fontSize: 11, fontWeight: "800", color: "#111" },
  productStrip: { paddingTop: 10 },
  sectionHeader: { flexDirection: "row-reverse", justifyContent: "space-between", alignItems: "center", paddingHorizontal: 16, marginBottom: 8 },
  sectionTitle: { fontSize: 17, fontWeight: "900", color: "#111" },
  seeAll: { fontSize: 11, color: "#555", fontWeight: "700" },
  productStripScroller: { paddingHorizontal: 16, gap: 10 },
  stripProduct: { width: 160 },
  stripProductCompact: { width: 138 },
  productRow: { width: "100%", maxWidth: contentWidth, alignSelf: "center", paddingHorizontal: screenWidth > 700 ? 16 : 8, gap: 8 },
  productCell: { flex: 1, minWidth: 0 },
  empty: { padding: 50, alignItems: "center", gap: 8 },
  emptyTitle: { fontSize: 15, fontWeight: "800", color: "#333" },
  emptyText: { fontSize: 12, color: "#888", textAlign: "center" },
});
