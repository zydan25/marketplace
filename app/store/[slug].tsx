import { useEffect, useState } from "react";
import { ActivityIndicator, FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ScreenContainer } from "@/components/screen-container";
import { ApiClient } from "@/lib/api-client";
import { ProductCard } from "@/components/product-card";
import { ShareButton } from "@/components/share-button";

export default function StoreScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const [store, setStore] = useState<any>(null);
  const [products, setProducts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      ApiClient.get(`/api/vendors/${slug}/`),
      ApiClient.get(`/api/products/?vendor=${slug}`)
    ]).then(([vendorData, productsData]: any) => {
      setStore(vendorData);
      setProducts(productsData.results || []);
    }).catch(console.error).finally(() => setLoading(false));
  }, [slug]);

  if (loading) return <ScreenContainer><View style={styles.center}><ActivityIndicator color="#E60023" /></View></ScreenContainer>;
  if (!store) return <ScreenContainer><View style={styles.center}><Text>المتجر غير موجود</Text></View></ScreenContainer>;

  return (
    <ScreenContainer edges={["top", "bottom", "left", "right"]} className="bg-[#F5F5F5]">
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}><MaterialIcons name="arrow-forward" size={25} /></TouchableOpacity>
        <Text style={styles.title}>{store.store_name}</Text>
        <ShareButton type="store" id={store.slug} title={store.store_name} />
      </View>
      
      <FlatList
        data={products}
        numColumns={2}
        keyExtractor={item => String(item.id)}
        contentContainerStyle={styles.list}
        columnWrapperStyle={styles.row}
        ListHeaderComponent={
          <View style={styles.storeInfo}>
            <View style={styles.logoPlaceholder}>
              <MaterialIcons name="storefront" size={40} color="#AAA" />
            </View>
            <Text style={styles.storeName}>{store.store_name}</Text>
            <Text style={styles.storeDesc}>{store.description || "مرحباً بكم في متجرنا"}</Text>
          </View>
        }
        renderItem={({ item }) => (
          <View style={styles.productWrapper}>
            <ProductCard product={item} />
          </View>
        )}
      />
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  header: { height: 54, paddingHorizontal: 16, backgroundColor: "#FFF", flexDirection: "row", justifyContent: "space-between", alignItems: "center", borderBottomWidth: 1, borderColor: "#F5F5F5" },
  title: { fontSize: 16, fontWeight: "900", color: "#111" },
  storeInfo: { alignItems: "center", padding: 24, backgroundColor: "#FFF", marginBottom: 16, borderRadius: 12, shadowColor: "#000", shadowOpacity: 0.03, shadowRadius: 8, elevation: 2 },
  logoPlaceholder: { width: 72, height: 72, borderRadius: 36, backgroundColor: "#F5F5F5", alignItems: "center", justifyContent: "center", marginBottom: 12 },
  storeName: { fontSize: 18, fontWeight: "900", color: "#111", marginBottom: 4 },
  storeDesc: { color: "#777", textAlign: "center", fontSize: 12, lineHeight: 20 },
  list: { padding: 16 },
  row: { justifyContent: "space-between", gap: 12, marginBottom: 0 },
  productWrapper: { flex: 1, maxWidth: "48%" }
});
