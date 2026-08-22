import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useMemo } from "react";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { ProductCard } from "@/components/product-card";
import { useProducts } from "@/hooks/use-products";

export default function CategoriesScreen() {
  const { products, loading, refresh } = useProducts();
  const insets = useSafeAreaInsets();
  const categories = useMemo(() => {
    const names = [...new Set(products.flatMap((product) =>
      product.categories?.length ? product.categories : [product.category],
    ).filter(Boolean))];
    return [{ id: "all", title: "الكل" }, ...names.map((title) => ({ id: title, title }))];
  }, [products]);
  const [selected] = ["all"];
  const visibleProducts = useMemo(
    () => selected === "all" ? products : products.filter((product) =>
      (product.categories?.length ? product.categories : [product.category]).includes(selected),
    ),
    [products, selected],
  );

  return (
    <View style={[styles.page, { paddingTop: Math.max(insets.top, 8) }]}>
      <View style={styles.header}>
        <TouchableOpacity style={styles.searchGhost} onPress={() => {}} activeOpacity={0.8}>
          <MaterialIcons name="photo-camera" size={19} color="#555" />
          <Text style={styles.searchText}>ابحث عن منتج أو فئة</Text>
          <MaterialIcons name="search" size={20} color="#171717" />
        </TouchableOpacity>
        <Text style={styles.title}>الفئات</Text>
      </View>
      <View style={styles.content}>
        <View style={styles.side}>
          <FlatList
            data={categories}
            keyExtractor={(item) => item.id}
            showsVerticalScrollIndicator={false}
            contentContainerStyle={styles.sideContent}
            renderItem={({ item }) => (
              <TouchableOpacity style={[styles.sideItem, selected === item.id && styles.sideItemActive]}>
                <Text style={[styles.sideText, selected === item.id && styles.sideTextActive]}>{item.title}</Text>
              </TouchableOpacity>
            )}
          />
        </View>
        <FlatList
          data={visibleProducts}
          keyExtractor={(item) => item.id}
          numColumns={2}
          showsVerticalScrollIndicator={false}
          columnWrapperStyle={styles.productRow}
          contentContainerStyle={[styles.products, { paddingBottom: 120 + insets.bottom }]}
          refreshing={loading}
          onRefresh={refresh}
          renderItem={({ item }) => <ProductCard product={item} />}
          ListHeaderComponent={
            <View style={styles.categoryHero}>
              <Text style={styles.categoryHeroText}>اكتشف منتجاتك حسب الفئة</Text>
              <Text style={styles.categoryHeroSub}>تصفح المنتجات المنشورة واختر ما يناسبك بسرعة.</Text>
            </View>
          }
          ListEmptyComponent={
            <View style={styles.empty}>
              <MaterialIcons name="category" size={40} color="#9D9D9D" />
              <Text style={styles.emptyText}>{loading ? "جارٍ تحميل المنتجات" : "لا توجد منتجات في هذه الفئة الآن"}</Text>
            </View>
          }
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: "#FFF" },
  header: { paddingHorizontal: 14, paddingBottom: 10, borderBottomWidth: 1, borderColor: "#EEE", flexDirection: "row-reverse", alignItems: "center", gap: 9 },
  title: { fontSize: 17, color: "#171717", fontWeight: "900" },
  searchGhost: { flex: 1, minWidth: 0, backgroundColor: "#F4F4F4", height: 40, paddingHorizontal: 10, borderRadius: 5, flexDirection: "row-reverse", alignItems: "center", gap: 7 },
  searchText: { flex: 1, color: "#727272", textAlign: "right", fontSize: 11 },
  content: { flex: 1, flexDirection: "row-reverse" },
  side: { width: 84, backgroundColor: "#F7F7F7" },
  sideContent: { paddingBottom: 120 },
  sideItem: { minHeight: 58, justifyContent: "center", alignItems: "center", paddingHorizontal: 7, borderRightWidth: 3, borderRightColor: "transparent" },
  sideItemActive: { backgroundColor: "#FFF", borderRightColor: "#171717" },
  sideText: { color: "#747474", textAlign: "center", fontSize: 11 },
  sideTextActive: { color: "#171717", fontWeight: "900" },
  products: { paddingHorizontal: 10, paddingTop: 10 },
  productRow: { gap: 9 },
  categoryHero: { minHeight: 92, marginBottom: 14, borderRadius: 12, backgroundColor: "#F0F0F0", justifyContent: "center", alignItems: "flex-end", padding: 14 },
  categoryHeroText: { color: "#171717", fontWeight: "900", fontSize: 18, textAlign: "right" },
  categoryHeroSub: { color: "#777", fontSize: 10, marginTop: 4, textAlign: "right", lineHeight: 16 },
  empty: { alignItems: "center", paddingTop: 30, width: "100%" },
  emptyText: { color: "#777", fontSize: 11, marginTop: 7, textAlign: "center" },
});
