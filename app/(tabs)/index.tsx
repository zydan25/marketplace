import { ActivityIndicator, RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";
import { useCallback, useState } from "react";

import { StorefrontBottomNavigation, StorefrontRenderer } from "@/components/storefront-renderer";
import { useCategories } from "@/hooks/use-categories";
import { useProducts } from "@/hooks/use-products";
import { useStorefront } from "@/hooks/use-storefront";

export default function StoreScreen() {
  const { products, loading: productsLoading, refresh: refreshProducts } = useProducts();
  const { tabs: sections, loading: storefrontLoading, refresh: refreshStorefront } = useStorefront();
  const { categories, loading: categoriesLoading, refresh: refreshCategories } = useCategories();
  const [refreshing, setRefreshing] = useState(false);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await Promise.all([refreshProducts(), refreshStorefront(), refreshCategories()]);
    } finally {
      setRefreshing(false);
    }
  }, [refreshCategories, refreshProducts, refreshStorefront]);

  const theme = sections.find((section) => Boolean((section.config as any)?.__theme))?.config?.__theme ?? null;
  const bottomNav = sections.find((section) => String(section.type).toLowerCase() === "bottom_nav");
  const showBottomNav = Boolean(bottomNav) && theme?.layout?.show_bottom_nav !== false;
  const primary = String(theme?.tokens?.primary ?? (theme?.layout?.family === "electronics" ? "#0D47A1" : "#E60023"));
  const loading = productsLoading || storefrontLoading || categoriesLoading;

  return (
    <View style={styles.page}>
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={[styles.content, showBottomNav && styles.contentWithBottomNav]}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} />}
        showsVerticalScrollIndicator={false}
      >
        {loading && sections.length === 0 ? (
          <View style={styles.loading}><ActivityIndicator size="large" /><Text style={styles.loadingText}>جارٍ تحميل المتجر...</Text></View>
        ) : sections.length === 0 ? (
          <View style={styles.empty}><Text style={styles.emptyTitle}>لا توجد واجهة منشورة</Text><Text style={styles.emptyText}>فعّل تصميمًا من مكتبة التصاميم ثم حدّث الصفحة.</Text></View>
        ) : (
          <StorefrontRenderer
            sections={sections as any}
            theme={theme}
            products={products}
            includeBottomNav={false}
            categories={categories.map((category) => ({ id: category.id, name: category.name, slug: category.slug, imageUrl: category.image ?? "" }))}
          />
        )}
      </ScrollView>
      {showBottomNav ? <View style={styles.fixedBottomNav}><StorefrontBottomNavigation config={(bottomNav?.config as any) ?? {}} primary={primary} /></View> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: "#FFF" },
  scroll: { flex: 1 },
  content: { paddingBottom: 24 },
  contentWithBottomNav: { paddingBottom: 96 },
  fixedBottomNav: { position: "absolute", left: 0, right: 0, bottom: 0, zIndex: 50, elevation: 12 },
  loading: { minHeight: 500, alignItems: "center", justifyContent: "center", gap: 10 },
  loadingText: { fontSize: 12, color: "#777" },
  empty: { minHeight: 500, alignItems: "center", justifyContent: "center", padding: 30 },
  emptyTitle: { fontSize: 18, fontWeight: "900", color: "#111" },
  emptyText: { marginTop: 7, fontSize: 12, color: "#777", textAlign: "center" },
});
