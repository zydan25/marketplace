import { useState, useEffect } from "react";
import { Alert, FlatList, StyleSheet, Text, TextInput, TouchableOpacity, View, ActivityIndicator, Switch } from "react-native";
import { router } from "expo-router";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ScreenContainer } from "@/components/screen-container";
import { djangoApi } from "@/lib/django-api";

type Product = { id: number; name: string; sku: string; effective_price: string; stock: number; is_published: boolean; currency: string };

export default function VendorProductsScreen() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [sku, setSku] = useState("");
  const [price, setPrice] = useState("");
  const [stock, setStock] = useState("");
  const [saving, setSaving] = useState(false);

  async function load() {
    try {
      setLoading(true);
      const data = await djangoApi<{ results?: Product[] }>("/api/products/");
      setProducts(data.results ?? []);
    } catch (error) {
      Alert.alert("تعذر التحميل", error instanceof Error ? error.message : "حدث خطأ");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function save() {
    if (!name.trim() || !sku.trim() || !price || !stock) return Alert.alert("بيانات ناقصة", "أكمل اسم المنتج والرقم والسعر والمخزون.");
    setSaving(true);
    try {
      await djangoApi("/api/products/", {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          sku: sku.trim(),
          slug: `${sku.toLowerCase().replace(/[^a-z0-9]/g, "-")}-${Date.now()}`,
          price,
          stock,
          is_published: true,
          currency: "YER"
        })
      });
      setName(""); setSku(""); setPrice(""); setStock(""); setShowForm(false);
      await load();
      Alert.alert("نجاح", "تمت إضافة المنتج بنجاح.");
    } catch (error) {
      Alert.alert("تعذر الحفظ", error instanceof Error ? error.message : "حدث خطأ");
    } finally { setSaving(false); }
  }

  async function togglePublish(product: Product) {
    try {
      await djangoApi(`/api/products/${product.id}/`, {
        method: "PATCH",
        body: JSON.stringify({ is_published: !product.is_published })
      });
      setProducts(current => current.map(p => p.id === product.id ? { ...p, is_published: !p.is_published } : p));
    } catch (error) {
      Alert.alert("خطأ", "تعذر تحديث حالة النشر.");
    }
  }

  async function deleteProduct(id: number) {
    Alert.alert("حذف المنتج", "هل أنت متأكد من حذف هذا المنتج نهائيًا؟", [
      { text: "إلغاء", style: "cancel" },
      {
        text: "حذف",
        style: "destructive",
        onPress: async () => {
          try {
            await djangoApi(`/api/products/${id}/`, { method: "DELETE" });
            setProducts(current => current.filter(p => p.id !== id));
          } catch (error) {
            Alert.alert("خطأ", "تعذر حذف المنتج.");
          }
        }
      }
    ]);
  }

  return (
    <ScreenContainer className="bg-[#F8F9FA]" edges={["top", "bottom", "left", "right"]}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}><MaterialIcons name="arrow-forward" size={24} color="#111" /></TouchableOpacity>
        <Text style={styles.title}>إدارة المنتجات</Text>
        <TouchableOpacity onPress={() => setShowForm(!showForm)} style={styles.addBtn}><MaterialIcons name={showForm ? "close" : "add"} size={24} color="#FFF" /></TouchableOpacity>
      </View>

      {showForm && (
        <View style={styles.form}>
          <Text style={styles.formTitle}>إضافة منتج جديد</Text>
          <TextInput style={styles.input} placeholder="اسم المنتج" value={name} onChangeText={setName} textAlign="right" />
          <TextInput style={styles.input} placeholder="رقم الصنف SKU" value={sku} onChangeText={setSku} textAlign="right" autoCapitalize="characters" />
          <View style={styles.row}>
            <TextInput style={[styles.input, styles.half]} placeholder="السعر (ر.ي)" value={price} onChangeText={setPrice} keyboardType="decimal-pad" textAlign="right" />
            <TextInput style={[styles.input, styles.half]} placeholder="المخزون" value={stock} onChangeText={setStock} keyboardType="number-pad" textAlign="right" />
          </View>
          <TouchableOpacity style={styles.save} onPress={save} disabled={saving}>
            {saving ? <ActivityIndicator color="#FFF" /> : <Text style={styles.saveText}>إضافة ونشر المنتج</Text>}
          </TouchableOpacity>
        </View>
      )}

      {loading ? (
        <View style={styles.center}><ActivityIndicator color="#E60023" /><Text style={styles.muted}>جارٍ تحميل المنتجات...</Text></View>
      ) : (
        <FlatList
          data={products}
          keyExtractor={(item) => String(item.id)}
          contentContainerStyle={styles.list}
          ListEmptyComponent={<View style={styles.emptyBox}><MaterialIcons name="inventory" size={48} color="#DDD" /><Text style={styles.empty}>لا توجد منتجات في متجرك حاليًا.</Text></View>}
          renderItem={({ item }) => (
            <View style={styles.card}>
              <View style={styles.cardMain}>
                <Text style={styles.productName}>{item.name}</Text>
                <Text style={styles.meta}>SKU: {item.sku} · المخزون: {item.stock}</Text>
                <View style={styles.statusRow}>
                  <Switch
                    value={item.is_published}
                    onValueChange={() => togglePublish(item)}
                    trackColor={{ true: "#168451", false: "#CCC" }}
                    style={{ transform: [{ scaleX: 0.8 }, { scaleY: 0.8 }] }}
                  />
                  <Text style={[styles.statusText, { color: item.is_published ? "#168451" : "#777" }]}>{item.is_published ? "منشور للعملاء" : "مسودة مخفية"}</Text>
                </View>
              </View>
              <View style={styles.cardActions}>
                <Text style={styles.priceText}>{item.effective_price} {item.currency}</Text>
                <View style={styles.btns}>
                  <TouchableOpacity onPress={() => deleteProduct(item.id)} style={styles.actionIcon}><MaterialIcons name="delete-outline" size={20} color="#E60023" /></TouchableOpacity>
                  <TouchableOpacity style={styles.actionIcon}><MaterialIcons name="edit" size={20} color="#444" /></TouchableOpacity>
                </View>
              </View>
            </View>
          )}
        />
      )}
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  header: { height: 60, paddingHorizontal: 16, flexDirection: "row-reverse", justifyContent: "space-between", alignItems: "center", backgroundColor: "#FFF", borderBottomWidth: 1, borderColor: "#EEE" },
  backBtn: { width: 40, height: 40, alignItems: "center", justifyContent: "center" },
  title: { fontSize: 18, fontWeight: "900", color: "#111" },
  addBtn: { width: 36, height: 36, borderRadius: 18, backgroundColor: "#E60023", alignItems: "center", justifyContent: "center" },
  form: { backgroundColor: "#FFF", margin: 12, padding: 16, borderRadius: 12, shadowColor: "#000", shadowOpacity: 0.05, shadowRadius: 10, elevation: 3 },
  formTitle: { fontSize: 16, fontWeight: "900", textAlign: "right", marginBottom: 15, color: "#111" },
  input: { backgroundColor: "#F8F9FA", borderWidth: 1, borderColor: "#E9ECEF", borderRadius: 8, padding: 12, marginBottom: 10, fontSize: 14, color: "#111" },
  row: { flexDirection: "row-reverse", gap: 10 },
  half: { flex: 1 },
  save: { backgroundColor: "#111", padding: 14, borderRadius: 8, alignItems: "center", marginTop: 5 },
  saveText: { color: "#FFF", fontWeight: "900", fontSize: 14 },
  list: { padding: 12, paddingBottom: 40 },
  card: { backgroundColor: "#FFF", borderRadius: 12, padding: 15, flexDirection: "row-reverse", justifyContent: "space-between", marginBottom: 10, borderWidth: 1, borderColor: "#F0F0F0" },
  cardMain: { flex: 1, alignItems: "flex-end" },
  productName: { fontWeight: "800", fontSize: 15, color: "#111", textAlign: "right" },
  meta: { color: "#777", fontSize: 11, marginTop: 4, textAlign: "right" },
  statusRow: { flexDirection: "row-reverse", alignItems: "center", marginTop: 8, gap: 5 },
  statusText: { fontSize: 11, fontWeight: "700" },
  cardActions: { alignItems: "flex-start", justifyContent: "space-between" },
  priceText: { color: "#E60023", fontSize: 16, fontWeight: "900" },
  btns: { flexDirection: "row", gap: 12, marginTop: 10 },
  actionIcon: { width: 34, height: 34, borderRadius: 17, backgroundColor: "#F8F9FA", alignItems: "center", justifyContent: "center" },
  center: { flex: 1, justifyContent: "center", alignItems: "center", gap: 10 },
  muted: { color: "#777", fontSize: 13 },
  emptyBox: { padding: 60, alignItems: "center" },
  empty: { color: "#999", textAlign: "center", marginTop: 15, fontSize: 14 },
});
