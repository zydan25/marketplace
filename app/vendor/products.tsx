import { useEffect, useState } from "react";
import { Alert, FlatList, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ScreenContainer } from "@/components/screen-container";
import { djangoApi } from "@/lib/django-api";

type Product = { id: number; name: string; sku: string; effective_price: string; stock: number; is_published: boolean };

export default function VendorProductsScreen() {
  const [products, setProducts] = useState<Product[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [sku, setSku] = useState("");
  const [price, setPrice] = useState("");
  const [stock, setStock] = useState("");
  const [saving, setSaving] = useState(false);

  async function load() {
    try {
      const data = await djangoApi<{ results?: Product[] }>("/api/products/");
      setProducts(data.results ?? []);
    } catch (error) {
      Alert.alert("تعذر التحميل", error instanceof Error ? error.message : "حدث خطأ");
    }
  }

  useEffect(() => { load(); }, []);

  async function save() {
    if (!name.trim() || !sku.trim() || !price || !stock) return Alert.alert("بيانات ناقصة", "أكمل اسم المنتج والرقم والسعر والمخزون.");
    setSaving(true);
    try {
      await djangoApi("/api/products/", { method: "POST", body: JSON.stringify({ name, sku, slug: `${sku.toLowerCase()}-${Date.now()}`, price, stock, is_published: false, currency: "YER" }) });
      setName(""); setSku(""); setPrice(""); setStock(""); setShowForm(false); await load();
    } catch (error) {
      Alert.alert("تعذر الحفظ", error instanceof Error ? error.message : "حدث خطأ");
    } finally { setSaving(false); }
  }

  return (
    <ScreenContainer className="bg-[#F5F5F5]" edges={["top", "bottom", "left", "right"]}>
      <View style={styles.header}><TouchableOpacity onPress={() => router.back()}><MaterialIcons name="arrow-forward" size={25} /></TouchableOpacity><Text style={styles.title}>منتجات المتجر</Text><TouchableOpacity onPress={() => setShowForm((value) => !value)}><MaterialIcons name={showForm ? "close" : "add"} size={25} color="#E60023" /></TouchableOpacity></View>
      {showForm && <View style={styles.form}>
        <Text style={styles.formTitle}>إضافة منتج سريع</Text>
        <TextInput style={styles.input} placeholder="اسم المنتج" value={name} onChangeText={setName} textAlign="right" />
        <TextInput style={styles.input} placeholder="رقم الصنف SKU" value={sku} onChangeText={setSku} textAlign="right" autoCapitalize="characters" />
        <View style={styles.row}><TextInput style={[styles.input, styles.half]} placeholder="السعر" value={price} onChangeText={setPrice} keyboardType="decimal-pad" textAlign="right" /><TextInput style={[styles.input, styles.half]} placeholder="المخزون" value={stock} onChangeText={setStock} keyboardType="number-pad" textAlign="right" /></View>
        <TouchableOpacity style={styles.save} onPress={save} disabled={saving}><Text style={styles.saveText}>{saving ? "جارٍ الحفظ..." : "حفظ كمسودة"}</Text></TouchableOpacity>
      </View>}
      <FlatList data={products} keyExtractor={(item) => String(item.id)} contentContainerStyle={styles.list} ListEmptyComponent={<Text style={styles.empty}>لا توجد منتجات. أضف أول منتج من الزر العلوي.</Text>} renderItem={({ item }) => <View style={styles.card}><View style={styles.cardMain}><Text style={styles.productName}>{item.name}</Text><Text style={styles.meta}>{item.sku} · المخزون {item.stock}</Text></View><View style={styles.price}><Text style={styles.priceText}>{item.effective_price}</Text><Text style={styles.meta}>{item.is_published ? "منشور" : "مسودة"}</Text></View></View>} />
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  header: { padding: 16, flexDirection: "row", justifyContent: "space-between", alignItems: "center", backgroundColor: "#FFF" },
  title: { fontSize: 20, fontWeight: "900" },
  form: { backgroundColor: "#FFF", margin: 12, padding: 14, borderRadius: 9 },
  formTitle: { fontSize: 17, fontWeight: "900", textAlign: "right", marginBottom: 12 },
  input: { backgroundColor: "#F7F7F7", borderWidth: 1, borderColor: "#E6E6E6", borderRadius: 7, padding: 13, marginBottom: 9, fontSize: 14 },
  row: { flexDirection: "row", gap: 9 },
  half: { flex: 1 },
  save: { backgroundColor: "#111", padding: 14, borderRadius: 7, alignItems: "center", marginTop: 3 },
  saveText: { color: "#FFF", fontWeight: "900" },
  list: { padding: 12, paddingBottom: 30 },
  card: { backgroundColor: "#FFF", borderRadius: 9, padding: 14, flexDirection: "row-reverse", justifyContent: "space-between", marginBottom: 8 },
  cardMain: { flex: 1 },
  productName: { textAlign: "right", fontWeight: "800", fontSize: 15 },
  meta: { color: "#777", fontSize: 11, marginTop: 5, textAlign: "right" },
  price: { alignItems: "flex-start", paddingLeft: 10 },
  priceText: { color: "#E60023", fontSize: 16, fontWeight: "900" },
  empty: { color: "#777", textAlign: "center", padding: 40, lineHeight: 24 },
});
