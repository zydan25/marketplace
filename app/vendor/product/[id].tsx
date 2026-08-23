import { useEffect, useState } from "react";
import { ActivityIndicator, Alert, Image, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ScreenContainer } from "@/components/screen-container";
import { djangoApi } from "@/lib/django-api";
import { formatYER } from "@/lib/catalog";

type Product = {
  id: number;
  name: string;
  sku: string;
  price: string;
  stock: number;
  main_image_url?: string | null;
  is_published: boolean;
  sales_count?: number;
  views_count?: number;
};

export default function VendorProductDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      setLoading(true);
      const data = await djangoApi<Product>(`/api/products/${id}/`);
      setProduct(data);
    } catch (error) {
      Alert.alert("تعذر التحميل", "لا يمكن عرض تفاصيل المنتج.");
      router.back();
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [id]);

  function confirmDelete() {
    Alert.alert("حذف المنتج", "سيتم حذف المنتج نهائيًا.", [
      { text: "إلغاء", style: "cancel" },
      { text: "حذف", style: "destructive", onPress: async () => {
        try {
          await djangoApi(`/api/products/${id}/`, { method: "DELETE" });
          router.replace("/vendor/products" as never);
        } catch {
          Alert.alert("خطأ", "تعذر حذف المنتج.");
        }
      }}
    ]);
  }

  if (loading) {
    return (
      <ScreenContainer edges={["top", "bottom", "left", "right"]} className="bg-[#F7F7F7]">
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.headerBtn}>
            <MaterialIcons name="arrow-forward" size={24} color="#111" />
          </TouchableOpacity>
        </View>
        <View style={styles.center}>
          <ActivityIndicator color="#E60023" size="large" />
        </View>
      </ScreenContainer>
    );
  }

  if (!product) return null;

  return (
    <ScreenContainer edges={["top", "bottom", "left", "right"]} className="bg-[#F7F7F7]">
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.headerBtn}>
          <MaterialIcons name="arrow-forward" size={24} color="#111" />
        </TouchableOpacity>
        <Text style={styles.title}>تفاصيل المنتج</Text>
        <TouchableOpacity onPress={() => router.replace("/vendor/products" as never)} style={styles.headerBtn}>
          <MaterialIcons name="home" size={24} color="#111" />
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.scroll} contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.imageContainer}>
          {product.main_image_url ? (
            <Image source={{ uri: product.main_image_url }} style={styles.mainImage} resizeMode="cover" />
          ) : (
            <MaterialIcons name="image" size={64} color="#CCC" />
          )}
        </View>

        <View style={styles.infoCard}>
          <Text style={styles.productName}>{product.name}</Text>
          <Text style={styles.productPrice}>{formatYER(Number(product.price))}</Text>
          <Text style={styles.productSku}>SKU: {product.sku}</Text>
        </View>

        <View style={styles.statsCard}>
          <View style={styles.statItem}>
            <Text style={styles.statValue}>{product.stock}</Text>
            <Text style={styles.statLabel}>المخزون</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statItem}>
            <Text style={styles.statValue}>{product.sales_count || 0}</Text>
            <Text style={styles.statLabel}>المبيعات</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statItem}>
            <Text style={styles.statValue}>{product.views_count || 0}</Text>
            <Text style={styles.statLabel}>الطلبات</Text>
          </View>
        </View>

        <View style={styles.actionsGrid}>
          <TouchableOpacity style={styles.actionBtn} onPress={() => router.push(`/vendor/product/create?edit=${product.id}` as never)}>
            <View style={styles.actionIconBox}><MaterialIcons name="edit" size={24} color="#111" /></View>
            <Text style={styles.actionLabel}>تعديل البيانات</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.actionBtn} onPress={() => Alert.alert("ميزة", "سيتم توفير إدارة المقاسات قريباً")}>
            <View style={styles.actionIconBox}><MaterialIcons name="straighten" size={24} color="#111" /></View>
            <Text style={styles.actionLabel}>المقاسات</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.actionBtn} onPress={() => Alert.alert("ميزة", "سيتم توفير إدارة الخصومات قريباً")}>
            <View style={styles.actionIconBox}><MaterialIcons name="local-offer" size={24} color="#111" /></View>
            <Text style={styles.actionLabel}>إضافة خصم</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.actionBtn} onPress={() => Alert.alert("ميزة", "سيتم توفير إدارة الصور قريباً")}>
            <View style={styles.actionIconBox}><MaterialIcons name="add-photo-alternate" size={24} color="#111" /></View>
            <Text style={styles.actionLabel}>إضافة صور</Text>
          </TouchableOpacity>
        </View>

        <TouchableOpacity style={styles.deleteBtn} onPress={confirmDelete}>
          <MaterialIcons name="delete-outline" size={20} color="#E60023" />
          <Text style={styles.deleteBtnText}>حذف المنتج</Text>
        </TouchableOpacity>
      </ScrollView>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  header: { height: 60, paddingHorizontal: 16, flexDirection: "row-reverse", justifyContent: "space-between", alignItems: "center", backgroundColor: "#FFF", borderBottomWidth: 1, borderColor: "#EEE" },
  headerBtn: { padding: 8 },
  title: { fontSize: 18, fontWeight: "900", color: "#111" },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  scroll: { flex: 1 },
  content: { padding: 16, paddingBottom: 100 },
  imageContainer: { width: "100%", height: 250, backgroundColor: "#FFF", borderRadius: 16, overflow: "hidden", alignItems: "center", justifyContent: "center", marginBottom: 16, borderWidth: 1, borderColor: "#EEE" },
  mainImage: { width: "100%", height: "100%" },
  infoCard: { backgroundColor: "#FFF", padding: 20, borderRadius: 16, marginBottom: 16, borderWidth: 1, borderColor: "#EEE", alignItems: "flex-end" },
  productName: { fontSize: 18, fontWeight: "900", color: "#111", textAlign: "right", marginBottom: 8 },
  productPrice: { fontSize: 20, fontWeight: "900", color: "#E60023", marginBottom: 8 },
  productSku: { fontSize: 13, color: "#777", fontWeight: "700" },
  statsCard: { flexDirection: "row-reverse", backgroundColor: "#FFF", padding: 16, borderRadius: 16, marginBottom: 16, borderWidth: 1, borderColor: "#EEE" },
  statItem: { flex: 1, alignItems: "center" },
  statValue: { fontSize: 20, fontWeight: "900", color: "#111", marginBottom: 4 },
  statLabel: { fontSize: 12, color: "#777", fontWeight: "700" },
  statDivider: { width: 1, backgroundColor: "#EEE", marginHorizontal: 10 },
  actionsGrid: { flexDirection: "row-reverse", flexWrap: "wrap", justifyContent: "space-between", marginBottom: 16 },
  actionBtn: { width: "48%", backgroundColor: "#FFF", padding: 16, borderRadius: 16, alignItems: "center", marginBottom: 16, borderWidth: 1, borderColor: "#EEE" },
  actionIconBox: { width: 48, height: 48, borderRadius: 24, backgroundColor: "#F7F7F7", alignItems: "center", justifyContent: "center", marginBottom: 12 },
  actionLabel: { fontSize: 13, fontWeight: "800", color: "#333" },
  deleteBtn: { flexDirection: "row-reverse", alignItems: "center", justifyContent: "center", backgroundColor: "#FFF", padding: 16, borderRadius: 16, borderWidth: 1, borderColor: "#FFDCDC", gap: 8 },
  deleteBtnText: { color: "#E60023", fontSize: 14, fontWeight: "800" },
});
