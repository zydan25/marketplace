import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { FlatList, Image, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useEffect, useMemo, useState } from "react";

import { ProductCard } from "@/components/product-card";
import { ShopHeader } from "@/components/shop-header";
import { useProducts } from "@/hooks/use-products";
import { useStorefront } from "@/hooks/use-storefront";
import { isAllStoreTab, shouldShowStoreProduct } from "@/lib/storefront-filter";

export default function StoreScreen() {
  const { products, loading: productsLoading, refresh: refreshProducts } = useProducts(); const { tabs, loading: storefrontLoading, refresh: refreshStorefront } = useStorefront(); const [activeTabId, setActiveTabId] = useState<string | null>(null); const [activeCircleId, setActiveCircleId] = useState<string | null>(null); const [slideIndex, setSlideIndex] = useState(0);
  useEffect(() => { if (!activeTabId && tabs[0]) setActiveTabId(tabs[0].id); if (activeTabId && !tabs.some((tab) => tab.id === activeTabId)) setActiveTabId(tabs[0]?.id ?? null); }, [activeTabId, tabs]);
  const activeTab = tabs.find((tab) => tab.id === activeTabId) ?? tabs[0]; const slides = activeTab?.slides ?? [];
  useEffect(() => { setSlideIndex(0); }, [activeTab?.id]); useEffect(() => { if (slides.length < 2) return; const timer = setInterval(() => setSlideIndex((current) => (current + 1) % slides.length), 4200); return () => clearInterval(timer); }, [slides.length]);
  const activeCircle = activeTab?.circles.find((circle) => circle.id === activeCircleId); const currentSlide = slides[slideIndex];
  const visibleProducts = useMemo(() => products.filter((product) => shouldShowStoreProduct(product, activeTab, activeCircle)), [activeCircle, activeTab, products]);
  const refresh = async () => { await Promise.all([refreshProducts(), refreshStorefront()]); };
  return <View style={styles.page}><FlatList data={visibleProducts} keyExtractor={(item) => item.id} numColumns={2} showsVerticalScrollIndicator={false} columnWrapperStyle={visibleProducts.length > 1 ? styles.productRow : undefined} contentContainerStyle={styles.listContent} renderItem={({ item }) => <ProductCard product={item} />} refreshing={productsLoading || storefrontLoading} onRefresh={refresh} ListHeaderComponent={<View><View style={styles.hero}>{currentSlide?.imageUrl ? <Image source={{ uri: currentSlide.imageUrl }} style={styles.heroImage} /> : <View style={styles.heroFallback} />}<View style={styles.heroShade} /><ShopHeader overlay placeholder={activeTab?.searchPlaceholder} /><FlatList horizontal inverted data={tabs} keyExtractor={(item) => item.id} showsHorizontalScrollIndicator={false} contentContainerStyle={styles.tabs} style={styles.tabsScroll} renderItem={({ item }) => <TouchableOpacity style={[styles.tab, activeTab?.id === item.id && styles.tabActive]} onPress={() => { setActiveTabId(item.id); setActiveCircleId(null); }}><Text style={[styles.tabText, activeTab?.id === item.id && styles.tabTextActive]}>{item.title}</Text></TouchableOpacity>} />{currentSlide ? <View style={styles.heroCopy}><Text style={styles.heroKicker}>{activeTab?.title}</Text><Text style={styles.heroTitle}>{currentSlide.title || "عرض جديد"}</Text>{currentSlide.subtitle ? <Text style={styles.heroSubtitle}>{currentSlide.subtitle}</Text> : null}<View style={styles.cta}><Text style={styles.ctaText}>{currentSlide.ctaLabel}</Text></View>{slides.length > 1 ? <View style={styles.dots}>{slides.map((_, index) => <View key={index} style={[styles.dot, index === slideIndex && styles.dotActive]} />)}</View> : null}</View> : <View style={styles.emptyHeroCopy}><Text style={styles.emptyHeroTitle}>{activeTab ? `لا توجد عروض لـ${activeTab.title} بعد` : "ابدئي بإضافة الشريط العلوي"}</Text><Text style={styles.emptyHeroText}>تُنشأ صور العروض من لوحة المدير وتظهر هنا خلف البحث والأيقونات.</Text></View>}</View>{activeTab?.circles.length ? <View style={styles.circlesArea}><FlatList horizontal inverted data={activeTab.circles} keyExtractor={(item) => item.id} showsHorizontalScrollIndicator={false} contentContainerStyle={styles.circleList} renderItem={({ item }) => <TouchableOpacity style={styles.circleItem} onPress={() => setActiveCircleId((current) => current === item.id ? null : item.id)}><View style={[styles.circleImageWrap, activeCircle?.id === item.id && styles.circleSelected]}>{item.imageUrl ? <Image source={{ uri: item.imageUrl }} style={styles.circleImage} /> : <MaterialIcons name="category" size={24} color="#808080" />}</View><Text numberOfLines={1} style={styles.circleLabel}>{item.title}</Text></TouchableOpacity>} /></View> : null}<View style={styles.sectionHeading}><Text style={styles.sectionTitle}>{activeCircle ? activeCircle.title : isAllStoreTab(activeTab) ? "كل الأصناف" : activeTab ? `منتجات ${activeTab.title}` : "أحدث الأصناف"}</Text><Text style={styles.sectionSub}>{isAllStoreTab(activeTab) ? "كل الفئات المنشورة" : "من الأصناف المنشورة"}</Text></View></View>} ListEmptyComponent={<View style={styles.empty}><MaterialIcons name="inventory-2" size={45} color="#9C9C9C" /><Text style={styles.emptyTitle}>{productsLoading || storefrontLoading ? "جارِ تحميل المتجر" : "لا توجد منتجات مطابقة بعد"}</Text><Text style={styles.emptyText}>تظهر المنتجات والصور بعد إضافتها من لوحة المدير ونشرها.</Text></View>} /></View>;
}
const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: "#F9F9F9" },
  listContent: { paddingBottom: 100 },
  hero: { height: 260, backgroundColor: "#111", position: "relative", overflow: "hidden" },
  heroImage: { position: "absolute", width: "100%", height: "100%" },
  heroFallback: { position: "absolute", width: "100%", height: "100%", backgroundColor: "#222" },
  heroShade: { position: "absolute", width: "100%", height: "100%", backgroundColor: "rgba(0,0,0,0.4)" },
  tabsScroll: { position: "absolute", top: 48, left: 0, right: 0, zIndex: 2 },
  tabs: { paddingHorizontal: 16, gap: 12 },
  tab: { paddingVertical: 6, borderBottomWidth: 2, borderBottomColor: "transparent" },
  tabActive: { borderBottomColor: "#FFF" },
  tabText: { color: "#EEE", fontSize: 13, textShadowColor: "rgba(0,0,0,0.5)", textShadowRadius: 4 },
  tabTextActive: { color: "#FFF", fontWeight: "900" },
  heroCopy: { position: "absolute", zIndex: 2, left: 20, right: 20, bottom: 24, alignItems: "flex-end" },
  heroKicker: { color: "#FFF", opacity: 0.8, fontSize: 11, fontWeight: "700" },
  heroTitle: { color: "#FFF", fontSize: 22, fontWeight: "900", textAlign: "right", marginTop: 4 },
  heroSubtitle: { color: "#FFF", opacity: 0.9, fontSize: 12, marginTop: 4, textAlign: "right" },
  cta: { backgroundColor: "#FFF", paddingHorizontal: 16, paddingVertical: 8, marginTop: 12, borderRadius: 20 },
  ctaText: { color: "#111", fontSize: 12, fontWeight: "800" },
  dots: { flexDirection: "row", gap: 6, marginTop: 16 },
  dot: { width: 6, height: 6, borderRadius: 3, backgroundColor: "rgba(255,255,255,0.4)" },
  dotActive: { width: 16, backgroundColor: "#FFF" },
  emptyHeroCopy: { position: "absolute", bottom: 24, left: 20, right: 20, alignItems: "flex-end" },
  emptyHeroTitle: { color: "#FFF", fontSize: 16, fontWeight: "900", textAlign: "right" },
  emptyHeroText: { color: "#DDD", fontSize: 11, textAlign: "right", marginTop: 4, lineHeight: 18 },
  circlesArea: { paddingTop: 20, paddingBottom: 8, backgroundColor: "#FFF" },
  circleList: { paddingHorizontal: 16, gap: 16 },
  circleItem: { width: 60, alignItems: "center" },
  circleImageWrap: { width: 56, height: 56, borderRadius: 28, backgroundColor: "#F5F5F5", overflow: "hidden", alignItems: "center", justifyContent: "center", borderWidth: 2, borderColor: "transparent" },
  circleSelected: { borderColor: "#111" },
  circleImage: { width: "100%", height: "100%" },
  circleLabel: { color: "#111", fontSize: 11, width: "100%", textAlign: "center", marginTop: 6, fontWeight: "500" },
  sectionHeading: { paddingHorizontal: 16, marginTop: 20, marginBottom: 12, alignItems: "flex-end" },
  sectionTitle: { color: "#111", fontSize: 16, fontWeight: "900" },
  sectionSub: { color: "#777", fontSize: 11, marginTop: 2 },
  productRow: { gap: 12, paddingHorizontal: 16 },
  empty: { alignItems: "center", paddingVertical: 40, paddingHorizontal: 24 },
  emptyTitle: { color: "#111", fontSize: 14, fontWeight: "900", marginTop: 12 },
  emptyText: { color: "#777", fontSize: 12, textAlign: "center", marginTop: 6 },
});
