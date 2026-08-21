import { FlatList, Image, StyleSheet, Text, TouchableOpacity, View, Dimensions, ScrollView } from "react-native";
import { useEffect, useMemo, useState, useCallback } from "react";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";

import { ProductCard } from "@/components/product-card";
import { ShopHeader } from "@/components/shop-header";
import { useProducts } from "@/hooks/use-products";
import { useStorefront } from "@/hooks/use-storefront";
import type { StorefrontTab } from "@/lib/storefront-api";
import { isAllStoreTab, shouldShowStoreProduct } from "@/lib/storefront-filter";

const { width } = Dimensions.get("window");

export default function StoreScreen() {
  const { products, loading: productsLoading, refresh: refreshProducts } = useProducts();
  const { tabs, loading: storefrontLoading, refresh: refreshStorefront } = useStorefront();
  const [activeTabId, setActiveTabId] = useState<string | null>(null);
  const [activeCircleId, setActiveCircleId] = useState<string | null>(null);
  const [slideIndex, setSlideIndex] = useState(0);
  const fallbackTabs = useMemo<StorefrontTab[]>(() => {
    const categoryNames = Array.from(new Set(products.flatMap((product) => product.categories))).filter(Boolean).slice(0, 12);
    const firstImage = products[0]?.images[0]?.url || "";
    return [{
      id: "fallback-all",
      title: "الكل",
      searchPlaceholder: "ابحثي عن منتج أو متجر",
      isActive: true,
      sortOrder: 0,
      slides: firstImage ? [{ id: "fallback-hero", title: "اختيارات تناسبك", subtitle: "تسوّقي أحدث المنتجات", ctaLabel: "تسوّقي الآن", imageUrl: firstImage, storageKey: "", isActive: true, sortOrder: 0 }] : [],
      circles: categoryNames.map((name, index) => ({ id: `fallback-circle-${index}`, title: name, targetCategory: name, imageUrl: products.find((product) => product.categories.includes(name))?.images[0]?.url || "", storageKey: "", isActive: true, sortOrder: index })),
    }];
  }, [products]);
  const displayTabs = tabs.length ? tabs : fallbackTabs;

  useEffect(() => {
    if (!activeTabId && displayTabs[0]) setActiveTabId(displayTabs[0].id);
    if (activeTabId && !displayTabs.some((tab) => tab.id === activeTabId)) setActiveTabId(displayTabs[0]?.id ?? null);
  }, [activeTabId, displayTabs]);

  const activeTab = displayTabs.find((tab) => tab.id === activeTabId) ?? displayTabs[0];
  const slides = activeTab?.slides ?? [];

  useEffect(() => {
    setSlideIndex(0);
  }, [activeTab?.id]);

  useEffect(() => {
    if (slides.length < 2) return;
    const timer = setInterval(() => setSlideIndex((current) => (current + 1) % slides.length), 5000);
    return () => clearInterval(timer);
  }, [slides.length]);

  const activeCircle = activeTab?.circles.find((circle) => circle.id === activeCircleId);
  const currentSlide = slides[slideIndex];

  const visibleProducts = useMemo(() =>
    products.filter((product) => shouldShowStoreProduct(product, activeTab, activeCircle)),
    [activeCircle, activeTab, products]
  );

  const refresh = async () => {
    await Promise.all([refreshProducts(), refreshStorefront()]);
  };

  return (
    <View style={styles.page}>
      <ShopHeader placeholder={activeTab?.searchPlaceholder} />

      <View style={styles.tabsContainer}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.tabsList}>
          {displayTabs.map((tab) => (
            <TouchableOpacity
              key={tab.id}
              style={[styles.tabItem, activeTab?.id === tab.id && styles.tabActive]}
              onPress={() => { setActiveTabId(tab.id); setActiveCircleId(null); }}
            >
              <Text style={[styles.tabText, activeTab?.id === tab.id && styles.tabTextActive]}>{tab.title}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>

      <FlatList
        data={visibleProducts}
        keyExtractor={(item) => item.id}
        numColumns={2}
        showsVerticalScrollIndicator={false}
        columnWrapperStyle={visibleProducts.length > 1 ? styles.productRow : undefined}
        contentContainerStyle={styles.listContent}
        refreshing={productsLoading || storefrontLoading}
        onRefresh={refresh}
        renderItem={({ item }) => <ProductCard product={item} />}
        ListHeaderComponent={
          <View>
            {/* Hero Banner Section */}
            <View style={styles.heroContainer}>
              {currentSlide?.imageUrl ? (
                <Image source={{ uri: currentSlide.imageUrl }} style={styles.heroImage} resizeMode="cover" />
              ) : (
                <View style={styles.heroFallback}><MaterialIcons name="image" size={40} color="#DDD" /></View>
              )}
              {currentSlide && (
                <View style={styles.heroOverlay}>
                  <View style={styles.heroBadge}><Text style={styles.heroBadgeText}>ترندات</Text></View>
                  <Text style={styles.heroTitle}>{currentSlide.title || "#فستان_رقيق"}</Text>
                  {currentSlide.subtitle ? <Text style={styles.heroSubtitle}>{currentSlide.subtitle}</Text> : null}
                  {slides.length > 1 && (
                    <View style={styles.dots}>
                      {slides.map((_, index) => <View key={index} style={[styles.dot, index === slideIndex && styles.dotActive]} />)}
                    </View>
                  )}
                </View>
              )}
            </View>

            {/* Flash Sale & Shipping Info */}
            <View style={styles.promoBar}>
              <View style={styles.promoItem}>
                <View style={styles.promoIcon}><MaterialIcons name="bolt" size={18} color="#111" /></View>
                <View><Text style={styles.promoTitle}>تخفيضات سريعة</Text><Text style={styles.promoLink}>عرض المزيد</Text></View>
              </View>
              <View style={styles.promoDivider} />
              <View style={styles.promoItem}>
                <View style={styles.promoIcon}><MaterialIcons name="local-shipping" size={18} color="#111" /></View>
                <View><Text style={styles.promoTitle}>شحن مجاني</Text><Text style={styles.promoSub}>أضيفي المزيد للحصول عليه</Text></View>
              </View>
            </View>

            {/* Circle Categories */}
            {activeTab?.circles.length ? (
              <View style={styles.circlesArea}>
                <FlatList
                  horizontal
                  inverted
                  data={activeTab.circles}
                  keyExtractor={(item) => item.id}
                  showsHorizontalScrollIndicator={false}
                  contentContainerStyle={styles.circleList}
                  renderItem={({ item }) => (
                    <TouchableOpacity style={styles.circleItem} onPress={() => setActiveCircleId((current) => current === item.id ? null : item.id)}>
                      <View style={[styles.circleImageWrap, activeCircle?.id === item.id && styles.circleSelected]}>
                        {item.imageUrl ? <Image source={{ uri: item.imageUrl }} style={styles.circleImage} /> : <MaterialIcons name="category" size={24} color="#808080" />}
                      </View>
                      <Text numberOfLines={1} style={styles.circleLabel}>{item.title}</Text>
                    </TouchableOpacity>
                  )}
                />
              </View>
            ) : null}

            {/* Filter Tabs */}
            <View style={styles.filterBar}>
              <FilterTab label="لكِ" active />
              <FilterTab label="وصل حديثًا" />
              <FilterTab label="العروض" />
              <FilterTab label="الأكثر مبيعًا" />
            </View>

            <View style={styles.sectionHeading}>
              <Text style={styles.sectionTitle}>{activeCircle ? activeCircle.title : isAllStoreTab(activeTab) ? "كل الأصناف" : activeTab ? `منتجات ${activeTab.title}` : "أحدث الأصناف"}</Text>
            </View>
          </View>
        }
        ListEmptyComponent={
          <View style={styles.empty}>
            <MaterialIcons name="inventory-2" size={45} color="#9C9C9C" />
            <Text style={styles.emptyTitle}>{productsLoading || storefrontLoading ? "جارِ تحميل المتجر" : "لا توجد منتجات مطابقة بعد"}</Text>
            <Text style={styles.emptyText}>تظهر المنتجات والصور بعد إضافتها من لوحة المدير ونشرها.</Text>
          </View>
        }
      />
    </View>
  );
}

function FilterTab({ label, active = false }: { label: string; active?: boolean }) {
  return (
    <TouchableOpacity style={[styles.filterTab, active && styles.filterTabActive]}>
      <Text style={[styles.filterTabText, active && styles.filterTabTextActive]}>{label}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: "#FFF" },
  tabsContainer: { backgroundColor: "#FFF", borderBottomWidth: 1, borderColor: "#F0F0F0" },
  tabsList: { paddingHorizontal: 12, gap: 20, height: 44, alignItems: "center" },
  tabItem: { paddingVertical: 10, borderBottomWidth: 2, borderBottomColor: "transparent" },
  tabActive: { borderBottomColor: "#111" },
  tabText: { fontSize: 14, color: "#777", fontWeight: "600" },
  tabTextActive: { color: "#111", fontWeight: "900" },
  listContent: { paddingBottom: 100 },
  heroContainer: { width: width, height: width * 0.8, backgroundColor: "#F5F5F5", position: "relative" },
  heroImage: { width: "100%", height: "100%" },
  heroFallback: { width: "100%", height: "100%", alignItems: "center", justifyContent: "center" },
  heroOverlay: { position: "absolute", bottom: 20, right: 20, alignItems: "flex-end" },
  heroBadge: { backgroundColor: "#8E44AD", paddingHorizontal: 8, paddingVertical: 4, borderRadius: 4 },
  heroBadgeText: { color: "#FFF", fontSize: 10, fontWeight: "800" },
  heroTitle: { color: "#FFF", fontSize: 28, fontWeight: "900", marginTop: 8, textShadowColor: "rgba(0,0,0,0.3)", textShadowRadius: 4 },
  heroSubtitle: { color: "#FFF", fontSize: 14, marginTop: 4, fontWeight: "600" },
  dots: { flexDirection: "row", gap: 6, marginTop: 12 },
  dot: { width: 6, height: 6, borderRadius: 3, backgroundColor: "rgba(255,255,255,0.5)" },
  dotActive: { width: 16, backgroundColor: "#FFF" },
  promoBar: { flexDirection: "row-reverse", backgroundColor: "#FFF9F0", paddingVertical: 12, paddingHorizontal: 16, alignItems: "center" },
  promoItem: { flex: 1, flexDirection: "row-reverse", alignItems: "center", gap: 8 },
  promoIcon: { width: 24, height: 24, alignItems: "center", justifyContent: "center" },
  promoTitle: { fontSize: 12, fontWeight: "900", color: "#111" },
  promoLink: { fontSize: 10, color: "#666", textDecorationLine: "underline", marginTop: 2 },
  promoSub: { fontSize: 10, color: "#666", marginTop: 2 },
  promoDivider: { width: 1, height: 30, backgroundColor: "#EEE", marginHorizontal: 10 },
  circlesArea: { paddingVertical: 20, backgroundColor: "#FFF" },
  circleList: { paddingHorizontal: 16, gap: 18 },
  circleItem: { width: 64, alignItems: "center" },
  circleImageWrap: { width: 60, height: 60, borderRadius: 30, backgroundColor: "#F8F8F8", overflow: "hidden", alignItems: "center", justifyContent: "center" },
  circleSelected: { borderWidth: 2, borderColor: "#111" },
  circleImage: { width: "100%", height: "100%" },
  circleLabel: { color: "#111", fontSize: 11, marginTop: 8, fontWeight: "600", textAlign: "center" },
  filterBar: { flexDirection: "row-reverse", paddingHorizontal: 12, gap: 8, marginBottom: 15 },
  filterTab: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 4, backgroundColor: "#F5F5F5" },
  filterTabActive: { backgroundColor: "#111" },
  filterTabText: { fontSize: 12, color: "#444", fontWeight: "700" },
  filterTabTextActive: { color: "#FFF" },
  sectionHeading: { paddingHorizontal: 16, marginBottom: 12, alignItems: "flex-end" },
  sectionTitle: { color: "#111", fontSize: 18, fontWeight: "900" },
  productRow: { gap: 12, paddingHorizontal: 12 },
  empty: { alignItems: "center", paddingVertical: 60, paddingHorizontal: 24 },
  emptyTitle: { color: "#111", fontSize: 15, fontWeight: "900", marginTop: 15 },
  emptyText: { color: "#777", fontSize: 13, textAlign: "center", marginTop: 8, lineHeight: 20 },
});
