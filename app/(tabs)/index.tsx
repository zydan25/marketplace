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
type StorefrontSectionConfig = Record<string, any>;

type BuilderTab = {
  id: string;
  title: string;
  productIds?: Array<number | string>;
  products?: Array<{ id: number | string }>;
  sortOrder?: number;
};

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
    () => visibleSections.find((section) => section.searchPlaceholder)?.searchPlaceholder ?? "ابحث عن منتج أو متجر",
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
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={refreshing || productsLoading || storefrontLoading || categoriesLoading} onRefresh={refresh} />}
        ListHeaderComponent={
          <View style={styles.headerContent}>
            {renderedSections.map((section) => (
              <StorefrontSection key={String(section.id)} section={section} products={products} />
            ))}
          </View>
        }
        renderItem={({ item }) => (
          <View style={styles.productCell}>
            <ProductCard product={item} />
          </View>
        )}
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
    searchPlaceholder: "ابحث عن منتج أو متجر",
    isActive: true,
    sortOrder: 0,
    slides: firstImage ? [{ id: "hero", title: "اختيارات مميزة", subtitle: "تسوّق أحدث المنتجات", imageUrl: firstImage, url: "/collection", badge: "", visible: true, isActive: true, sortOrder: 0, ctaLabel: "تسوّق الآن" } satisfies StorefrontSlide] : [],
    circles: categories.slice(0, 12).map((category, index) => ({ id: String(index), title: category.name, targetCategory: category.name, imageUrl: "", url: `/collection?category=${encodeURIComponent(category.name)}`, visible: true, isActive: true, sortOrder: index } satisfies StorefrontCircle)),
    cards: [] as StorefrontCard[],
    actions: [],
    promo: { enabled: false, flashTitle: "", flashSubtitle: "", flashMode: "", freeShippingTitle: "", freeShippingSubtitle: "", freeShippingCategory: "" },
    config: { showGlobalGrid: true },
  }];
}

function StorefrontSection({ section, products }: { section: StorefrontTab; products: StoreProduct[] }) {
  const config = (section.config ?? {}) as StorefrontSectionConfig;
  const sectionType = section.type.toLowerCase();
  return <View style={styles.section}>
    {(sectionType === "hero" || sectionType === "banner" || section.slides.length > 0) && section.slides.length > 0 ? <HeroBlock slides={section.slides} /> : null}
    {(sectionType === "category" || section.circles.length > 0) && section.circles.length > 0 ? <CircleBlock circles={section.circles} /> : null}
    {(sectionType === "banner" || section.cards.length > 0) && section.cards.length > 0 ? <CardsBlock cards={section.cards} /> : null}
    {section.promo?.enabled ? <PromoBlock promo={section.promo} /> : null}
    {section.actions.length > 0 ? <ActionBlock actions={section.actions} /> : null}
    {(sectionType === "product_grid" || sectionType === "trend" || config.showProducts === true || config.showGlobalGrid === true) ? (
      <ProductSection section={section} products={products} />
    ) : null}
  </View>;
}

function ProductSection({ section, products }: { section: StorefrontTab; products: StoreProduct[] }) {
  const config = (section.config ?? {}) as StorefrontSectionConfig;
  const tabs = Array.isArray(config.tabs) ? (config.tabs as BuilderTab[]).sort((a, b) => Number(a.sortOrder ?? 0) - Number(b.sortOrder ?? 0)) : [];
  const [activeTab, setActiveTab] = useState<string>(tabs[0]?.id ? String(tabs[0].id) : "all");

  const baseIds = Array.isArray(config.resolved_product_ids)
    ? config.resolved_product_ids.map(String)
    : Array.isArray(config.productIds)
      ? config.productIds.map(String)
      : null;
  const tab = tabs.find((item) => String(item.id) === activeTab);
  const tabIds = tab
    ? (Array.isArray(tab.productIds)
      ? tab.productIds.map(String)
      : Array.isArray(tab.products)
        ? tab.products.map((item) => String(item.id))
        : null)
    : null;
  const chosenIds = tabIds?.length ? new Set(tabIds) : baseIds?.length ? new Set(baseIds) : null;
  const filtered = products.filter((item) => !chosenIds || chosenIds.has(String(item.id)));
  const source = String(config.source ?? "latest");
  const category = String(config.category ?? config.category_name ?? "").trim();
  const categoryFiltered = category ? filtered.filter((item) => item.categories.some((name) => name.trim() === category)) : filtered;
  const sorted = source === "trending"
    ? categoryFiltered.filter((item) => item.isTrending).sort((a, b) => b.reviews - a.reviews)
    : source === "best_selling"
      ? [...categoryFiltered].sort((a, b) => b.reviews - a.reviews)
      : source === "discounts"
        ? categoryFiltered.filter((item) => item.discountPercent > 0)
        : categoryFiltered;
  const rows = Math.max(1, Math.min(Number(config.rows ?? 2), 8));
  const columns = Math.max(1, Math.min(Number(screenWidth > 700 ? config.columns ?? config.columns_desktop ?? 4 : config.columns_mobile ?? 2), 6));
  const limit = Math.max(1, rows * columns);
  const items = sorted.slice(0, limit);
  const showCategories = Boolean(config.show_categories && Array.isArray(config.category_circles) && config.category_circles.length);

  return <View style={styles.productSection}>
    <SectionHeading title={section.title || (source === "trending" ? "الأكثر رواجًا" : "منتجات مختارة")} />
    {tabs.length > 0 ? <TabBar tabs={tabs} active={activeTab} onSelect={setActiveTab} /> : null}
    {showCategories ? <CircleBlock circles={config.category_circles as StorefrontCircle[]} /> : null}
    {!items.length ? <Text style={styles.sectionEmpty}>لا توجد منتجات مطابقة لإعدادات هذا القسم.</Text> : (
      config.scroll === false ? (
        <View style={styles.gridProducts}>{items.map((item) => <View key={item.id} style={{ width: `${100 / columns}%`, padding: 5 }}><ProductCard product={item} /></View>)}</View>
      ) : (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.productStripScroller}>
          {items.map((item) => <View key={item.id} style={[styles.stripProduct, config.card_style === "compact" && styles.stripProductCompact]}><ProductCard product={item} /></View>)}
        </ScrollView>
      )
    )}
  </View>;
}

function SectionHeading({ title }: { title: string }) {
  return <View style={styles.sectionHeader}><Text style={styles.sectionTitle}>{title}</Text><Pressable onPress={() => router.push("/collection" as never)}><Text style={styles.seeAll}>عرض الكل</Text></Pressable></View>;
}

function TabBar({ tabs, active, onSelect }: { tabs: BuilderTab[]; active: string; onSelect: (value: string) => void }) {
  return <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.tabBar}>
    {tabs.map((tab) => <Pressable key={String(tab.id)} onPress={() => onSelect(String(tab.id))} style={[styles.tabChip, active === String(tab.id) && styles.tabChipActive]}><Text style={[styles.tabChipText, active === String(tab.id) && styles.tabChipTextActive]}>{tab.title}</Text></Pressable>)}
  </ScrollView>;
}

function HeroBlock({ slides }: { slides: StorefrontSlide[] }) {
  const visible = slides.filter((item) => item.visible !== false && item.isActive !== false);
  if (!visible.length) return null;
  return <ScrollView horizontal pagingEnabled showsHorizontalScrollIndicator={false} contentContainerStyle={styles.heroScroller}>
    {visible.map((slide, index) => <Pressable key={String(slide.id ?? index)} style={styles.hero} onPress={() => navigateUrl(slide.url)} accessibilityRole="button">
      {slide.imageUrl ? <Image source={{ uri: slide.imageUrl }} style={styles.heroImage} resizeMode="cover" /> : <View style={styles.heroPlaceholder}><MaterialIcons name="image" size={36} color="#aaa" /></View>}
      <View style={styles.heroShade} />
      <View style={styles.heroText}>{slide.badge ? <Text style={styles.badge}>{slide.badge}</Text> : null}<Text style={styles.heroTitle}>{slide.title}</Text>{slide.subtitle ? <Text style={styles.heroSubtitle}>{slide.subtitle}</Text> : null}{slide.ctaLabel ? <View style={styles.heroButton}><Text style={styles.heroButtonText}>{slide.ctaLabel}</Text><MaterialIcons name="arrow-back" size={16} color="#111" /></View> : null}</View>
    </Pressable>)}
  </ScrollView>;
}

function CircleBlock({ circles }: { circles: StorefrontCircle[] }) {
  const visible = circles.filter((circle) => circle.visible !== false && circle.isActive !== false);
  if (!visible.length) return null;
  return <View style={styles.circleArea}><ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.circleScroller}>{visible.map((circle) => <Pressable key={String(circle.id)} style={styles.circleItem} onPress={() => navigateUrl(circle.url || `/collection?category=${encodeURIComponent(circle.targetCategory || circle.title)}`)}><View style={styles.circleImage}>{circle.imageUrl ? <Image source={{ uri: circle.imageUrl }} style={StyleSheet.absoluteFillObject} /> : <MaterialIcons name="category" size={24} color="#777" />}</View><Text numberOfLines={1} style={styles.circleText}>{circle.title}</Text></Pressable>)}</ScrollView></View>;
}

function CardsBlock({ cards }: { cards: StorefrontCard[] }) {
  const visible = cards.filter((card) => card.visible !== false && card.isActive !== false);
  if (!visible.length) return null;
  return <View style={styles.cardsWrap}><ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.cardsScroller}>{visible.map((card) => <Pressable key={card.id} style={styles.contentCard} onPress={() => navigateUrl(card.url)}>{card.imageUrl ? <Image source={{ uri: card.imageUrl }} style={styles.cardImage} /> : <View style={styles.cardImageFallback}><MaterialIcons name="image" size={28} color="#aaa" /></View>}<View style={styles.cardBody}>{card.badge ? <Text style={styles.cardBadge}>{card.badge}</Text> : null}<Text style={styles.cardTitle}>{card.title}</Text>{card.subtitle ? <Text numberOfLines={2} style={styles.cardSubtitle}>{card.subtitle}</Text> : null}</View></Pressable>)}</ScrollView></View>;
}

function PromoBlock({ promo }: { promo: NonNullable<StorefrontTab["promo"]> }) {
  return <View style={styles.promo}><View style={styles.promoItem}><MaterialIcons name="bolt" size={19} color="#111" /><View><Text style={styles.promoTitle}>{promo.flashTitle}</Text><Text style={styles.promoSub}>{promo.flashSubtitle}</Text></View></View><View style={styles.promoDivider} /><View style={styles.promoItem}><MaterialIcons name="local-shipping" size={19} color="#111" /><View><Text style={styles.promoTitle}>{promo.freeShippingTitle}</Text><Text style={styles.promoSub}>{promo.freeShippingSubtitle}</Text></View></View></View>;
}

function ActionBlock({ actions }: { actions: { label: string; url: string; visible: boolean }[] }) {
  const visible = actions.filter((action) => action.visible !== false && action.label.trim());
  if (!visible.length) return null;
  return <View style={styles.actions}>{visible.map((action, index) => <Pressable key={`${action.label}-${index}`} style={styles.action} onPress={() => navigateUrl(action.url)}><Text style={styles.actionText}>{action.label}</Text><MaterialIcons name="arrow-back" size={16} color="#111" /></Pressable>)}</View>;
}

function navigateUrl(url: string) {
  const value = url.trim();
  if (!value) return;
  if (value.startsWith("/")) { router.push(value as never); return; }
  if (/^https?:\/\//i.test(value)) void Linking.openURL(value);
}

function EmptyState({ loading }: { loading: boolean }) {
  return <View style={styles.empty}><MaterialIcons name="inventory-2" size={44} color="#aaa" /><Text style={styles.emptyTitle}>{loading ? "جارٍ تحميل المتجر" : "لا توجد منتجات متاحة"}</Text><Text style={styles.emptyText}>يمكن للإدارة التحكم بالأقسام والمنتجات من لوحة المنصة.</Text></View>;
}

const styles = StyleSheet.create({
  page:{flex:1,backgroundColor:"#fff"},list:{flex:1},listContent:{paddingBottom:110},headerContent:{width:"100%",maxWidth:contentWidth,alignSelf:"center"},section:{width:"100%"},heroScroller:{gap:10},hero:{width:Math.min(screenWidth,1180),maxWidth:1180,marginTop:12,borderRadius:screenWidth>700?18:0,overflow:"hidden",height:Math.min(460,Math.max(260,screenWidth*0.68)),backgroundColor:"#f5f5f5",position:"relative"},heroImage:{width:"100%",height:"100%"},heroPlaceholder:{flex:1,alignItems:"center",justifyContent:"center",backgroundColor:"#eee"},heroShade:{...StyleSheet.absoluteFillObject,backgroundColor:"rgba(0,0,0,.25)"},heroText:{position:"absolute",right:22,bottom:22,maxWidth:"74%",alignItems:"flex-end"},badge:{backgroundColor:"#fff",color:"#111",fontSize:10,fontWeight:"800",paddingHorizontal:8,paddingVertical:4,borderRadius:99},heroTitle:{color:"#fff",fontSize:screenWidth>700?31:25,fontWeight:"900",textAlign:"right",marginTop:9},heroSubtitle:{color:"#fff",fontSize:13,textAlign:"right",marginTop:5},heroButton:{marginTop:12,backgroundColor:"#fff",borderRadius:22,paddingHorizontal:14,paddingVertical:10,flexDirection:"row-reverse",alignItems:"center",gap:6},heroButtonText:{color:"#111",fontSize:12,fontWeight:"800"},circleArea:{paddingVertical:14},circleScroller:{paddingHorizontal:16,gap:18},circleItem:{width:68,alignItems:"center"},circleImage:{width:62,height:62,borderRadius:31,backgroundColor:"#f4f4f4",overflow:"hidden",alignItems:"center",justifyContent:"center",borderWidth:1,borderColor:"#eee"},circleText:{fontSize:11,color:"#333",fontWeight:"700",marginTop:7,maxWidth:68,textAlign:"center"},cardsWrap:{paddingVertical:6},cardsScroller:{paddingHorizontal:16,gap:12},contentCard:{width:250,borderRadius:16,overflow:"hidden",backgroundColor:"#fff",borderWidth:1,borderColor:"#eee"},cardImage:{width:"100%",height:145,backgroundColor:"#f5f5f5"},cardImageFallback:{width:"100%",height:145,backgroundColor:"#f5f5f5",alignItems:"center",justifyContent:"center"},cardBody:{padding:12,alignItems:"flex-end"},cardBadge:{fontSize:10,color:"#8b5cf6",fontWeight:"800",marginBottom:3},cardTitle:{fontSize:15,fontWeight:"900",color:"#111",textAlign:"right"},cardSubtitle:{fontSize:11,color:"#777",lineHeight:18,textAlign:"right"},promo:{marginHorizontal:16,marginVertical:12,padding:13,borderRadius:14,backgroundColor:"#F7F7F7",flexDirection:"row-reverse",alignItems:"center"},promoItem:{flex:1,flexDirection:"row-reverse",alignItems:"center",gap:8},promoDivider:{width:1,height:30,backgroundColor:"#DDD",marginHorizontal:10},promoTitle:{fontSize:11,fontWeight:"900",color:"#111",textAlign:"right"},promoSub:{fontSize:9,color:"#777",marginTop:3,textAlign:"right"},actions:{paddingHorizontal:16,paddingVertical:8,gap:8},action:{minHeight:44,paddingHorizontal:14,borderRadius:12,backgroundColor:"#F5F5F5",flexDirection:"row-reverse",alignItems:"center",justifyContent:"space-between"},actionText:{fontSize:12,fontWeight:"800",color:"#111"},productSection:{paddingVertical:12},sectionHeader:{paddingHorizontal:16,flexDirection:"row-reverse",alignItems:"center",justifyContent:"space-between",marginBottom:7},sectionTitle:{fontSize:17,fontWeight:"900",color:"#111"},seeAll:{fontSize:11,fontWeight:"800",color:"#777"},tabBar:{paddingHorizontal:16,gap:8,paddingBottom:8},tabChip:{paddingHorizontal:13,paddingVertical:8,borderRadius:18,backgroundColor:"#F2F2F2"},tabChipActive:{backgroundColor:"#111"},tabChipText:{color:"#555",fontSize:11,fontWeight:"800"},tabChipTextActive:{color:"#fff"},productStripScroller:{paddingHorizontal:16,gap:12},stripProduct:{width:160},stripProductCompact:{width:135},gridProducts:{paddingHorizontal:11,flexDirection:"row",flexWrap:"wrap"},productRow:{gap:8,paddingHorizontal:12},productCell:{flex:1,minWidth:0},sectionEmpty:{paddingHorizontal:16,paddingVertical:18,textAlign:"right",color:"#888",fontSize:11},empty:{alignItems:"center",justifyContent:"center",paddingVertical:80,paddingHorizontal:30},emptyTitle:{fontSize:16,fontWeight:"900",color:"#333",marginTop:10},emptyText:{fontSize:12,color:"#777",textAlign:"center",marginTop:6}
});
