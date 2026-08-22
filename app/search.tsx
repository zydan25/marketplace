import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { Alert, FlatList, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { useMemo, useState } from "react";
import { router } from "expo-router";
import { ProductCard } from "@/components/product-card";
import { ScreenContainer } from "@/components/screen-container";
import { useProducts } from "@/hooks/use-products";
import type { StoreProduct } from "@/lib/product-api";

const quickFilters = ["خصومات", "أقل من 20 ألف"];

export default function SearchScreen() {
  const { products, loading, refresh } = useProducts();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("");
  const [photoResults, setPhotoResults] = useState<StoreProduct[] | null>(null);
  const matches = useMemo(() => {
    if (photoResults) return photoResults;
    const normalized = query.trim().toLowerCase();
    return products.filter((product) => {
      const content = `${product.productCode} ${product.name} ${product.category} ${product.description} ${product.details} ${product.trendTags.join(" ")}`.toLowerCase();
      return (!normalized || content.includes(normalized)) && (!filter || (filter === "خصومات" ? product.discountPercent > 0 : product.price < 20000));
    });
  }, [filter, photoResults, products, query]);

  const searchImage = () => Alert.alert("البحث بالصورة", "سيتم تفعيل البحث البصري بعد ربط محرك الصور بالـDjango API الموحد.");
  const clearPhoto = () => setPhotoResults(null);

  return (
    <ScreenContainer edges={["top", "left", "right", "bottom"]} className="bg-white">
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.back} accessibilityLabel="رجوع"><MaterialIcons name="arrow-forward" size={23} color="#171717" /></TouchableOpacity>
        <View style={styles.inputWrap}>
          <MaterialIcons name="search" size={21} color="#666" />
          <TextInput value={query} onChangeText={(value) => { setQuery(value); if (photoResults) clearPhoto(); }} autoFocus placeholder="ابحث عن الاسم أو رقم الصنف أو الهاشتاج" placeholderTextColor="#898989" style={styles.input} textAlign="right" />
          <TouchableOpacity onPress={searchImage}><MaterialIcons name="photo-camera" size={20} color="#444" /></TouchableOpacity>
        </View>
      </View>
      <FlatList
        data={matches}
        keyExtractor={(item) => item.id}
        numColumns={2}
        showsVerticalScrollIndicator={false}
        columnWrapperStyle={matches.length > 1 ? styles.row : undefined}
        contentContainerStyle={styles.content}
        refreshing={loading}
        onRefresh={refresh}
        renderItem={({ item }) => <ProductCard product={item} />}
        ListHeaderComponent={<View>{photoResults ? <View style={styles.imageSearch}><MaterialIcons name="image-search" size={18} color="#E60023" /><Text style={styles.imageSearchText}>نتائج البحث البصري</Text><TouchableOpacity onPress={clearPhoto}><Text style={styles.clear}>مسح</Text></TouchableOpacity></View> : <><Text style={styles.heading}>{query ? `نتائج البحث عن «${query}»` : "اكتشف المنتجات"}</Text><Text style={styles.hint}>ابحث بالاسم أو رقم الصنف أو الوصف أو كلمات الترند.</Text><FlatList horizontal inverted data={quickFilters} keyExtractor={(item) => item} showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filters} renderItem={({ item }) => <TouchableOpacity onPress={() => setFilter(filter === item ? "" : item)} style={[styles.filter, filter === item && styles.filterActive]}><Text style={[styles.filterText, filter === item && styles.filterTextActive]}>{item}</Text></TouchableOpacity>} /></>}</View>}
        ListEmptyComponent={<View style={styles.empty}><MaterialIcons name="search-off" size={42} color="#A0A0A0" /><Text style={styles.emptyText}>{products.length ? "لم نجد نتائج مطابقة. جرّب كلمة أخرى أو رقم صنف مختلفًا." : "سيصبح البحث متاحًا بعد إضافة المنتجات من الإدارة."}</Text></View>}
      />
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  header: { minHeight: 57, paddingHorizontal: 12, flexDirection: "row-reverse", gap: 8, alignItems: "center", borderBottomWidth: 1, borderColor: "#EEE" },
  back: { width: 36, height: 36, borderRadius: 18, alignItems: "center", justifyContent: "center", backgroundColor: "#F6F6F6" },
  inputWrap: { height: 40, backgroundColor: "#F3F3F3", borderRadius: 9, flex: 1, minWidth: 0, flexDirection: "row-reverse", alignItems: "center", paddingHorizontal: 10, gap: 7 },
  input: { flex: 1, minWidth: 0, color: "#171717", fontSize: 12, writingDirection: "rtl" },
  content: { padding: 12, paddingBottom: 125 },
  heading: { color: "#171717", fontSize: 17, fontWeight: "900", textAlign: "right", marginBottom: 5 },
  hint: { color: "#777", fontSize: 10, textAlign: "right", marginBottom: 11, lineHeight: 16 },
  filters: { gap: 8, paddingBottom: 14 },
  filter: { borderWidth: 1, borderColor: "#DFDFDF", paddingHorizontal: 11, paddingVertical: 7, borderRadius: 18 },
  filterActive: { backgroundColor: "#171717", borderColor: "#171717" },
  filterText: { color: "#4E4E4E", fontSize: 10, fontWeight: "700" },
  filterTextActive: { color: "#FFF" },
  row: { gap: 10 },
  empty: { alignItems: "center", paddingVertical: 45, paddingHorizontal: 18 },
  emptyText: { color: "#777", fontSize: 12, marginTop: 8, textAlign: "center", lineHeight: 18 },
  imageSearch: { backgroundColor: "#FFF1F3", padding: 10, borderRadius: 10, flexDirection: "row-reverse", alignItems: "center", gap: 7, marginBottom: 12 },
  imageSearchText: { flex: 1, color: "#A4001A", fontSize: 11, textAlign: "right" },
  clear: { color: "#E60023", fontWeight: "900", fontSize: 11 },
});
