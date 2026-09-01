import { ActivityIndicator, RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";
import { useCallback, useState } from "react";

import { StorefrontRenderer } from "@/components/storefront-renderer";
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
  const loading = productsLoading || storefrontLoading || categoriesLoading;

  return (
    <ScrollView
      style={styles.page}
      contentContainerStyle={styles.content}
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
          categories={categories.map((category) => ({ id: category.id, name: category.name, slug: category.slug, imageUrl: category.image ?? "" }))}
        />
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: "#FFF" },
  content: { paddingBottom: 96 },
  loading: { minHeight: 500, alignItems: "center", justifyContent: "center", gap: 10 },
  loadingText: { fontSize: 12, color: "#777" },
  empty: { minHeight: 500, alignItems: "center", justifyContent: "center", padding: 30 },
  emptyTitle: { fontSize: 18, fontWeight: "900", color: "#111" },
  emptyText: { marginTop: 7, fontSize: 12, color: "#777", textAlign: "center" },
});
