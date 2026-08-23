import { useEffect, useState } from "react";
import { ActivityIndicator, Alert, FlatList, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ScreenContainer } from "@/components/screen-container";
import { djangoApi } from "@/lib/django-api";

type Category = {
  id: number;
  name: string;
  slug: string;
  description?: string;
};

type CategoryListResponse = Category[] | { results?: Category[] };

export default function VendorCategoriesScreen() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState("");

  async function load() {
    try {
      setLoading(true);
      const data = await djangoApi<CategoryListResponse>("/api/categories/");
      setCategories(Array.isArray(data) ? data : (data.results ?? []));
    } catch (error) {
      Alert.alert("تعذر التحميل", "لا يمكن جلب الأصناف حاليًا.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function handleAddCategory() {
    if (!newCategoryName.trim()) return;
    setAdding(true);
    try {
      const slug = newCategoryName.trim().toLowerCase().replace(/\s+/g, '-');
      const payload = { name: newCategoryName.trim(), slug };
      const newCat = await djangoApi<Category>("/api/categories/", {
        method: "POST",
        body: JSON.stringify(payload)
      });
      setCategories(prev => [...prev, newCat]);
      setNewCategoryName("");
      Alert.alert("تم", "تمت إضافة الصنف بنجاح.");
    } catch (error) {
      Alert.alert("تعذر الإضافة", "تأكد من أن الاسم غير مكرر.");
    } finally {
      setAdding(false);
    }
  }

  return (
    <ScreenContainer edges={["top", "bottom", "left", "right"]} className="bg-[#F7F7F7]">
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.headerBtn}>
          <MaterialIcons name="arrow-forward" size={24} color="#111" />
        </TouchableOpacity>
        <Text style={styles.title}>إدارة الأصناف</Text>
        <View style={{ width: 40 }} />
      </View>

      <View style={styles.addSection}>
        <Text style={styles.sectionTitle}>إضافة صنف جديد</Text>
        <View style={styles.inputRow}>
          <TouchableOpacity 
            style={[styles.addBtn, (!newCategoryName.trim() || adding) && styles.addBtnDisabled]} 
            onPress={handleAddCategory}
            disabled={!newCategoryName.trim() || adding}
          >
            {adding ? <ActivityIndicator color="#FFF" size="small" /> : <Text style={styles.addBtnText}>إضافة</Text>}
          </TouchableOpacity>
          <TextInput
            style={styles.input}
            placeholder="اسم الصنف (مثال: أحذية نسائية)"
            value={newCategoryName}
            onChangeText={setNewCategoryName}
            textAlign="right"
          />
        </View>
      </View>

      <View style={styles.listContainer}>
        <Text style={styles.sectionTitle}>الأصناف المتوفرة</Text>
        {loading ? (
          <View style={styles.center}>
            <ActivityIndicator color="#E60023" />
          </View>
        ) : (
          <FlatList
            data={categories}
            keyExtractor={item => String(item.id)}
            contentContainerStyle={styles.listContent}
            ListEmptyComponent={
              <View style={styles.emptyBox}>
                <Text style={styles.emptyText}>لا توجد أصناف حاليًا.</Text>
              </View>
            }
            renderItem={({ item }) => (
              <View style={styles.categoryCard}>
                <MaterialIcons name="category" size={24} color="#777" />
                <Text style={styles.categoryName}>{item.name}</Text>
              </View>
            )}
          />
        )}
      </View>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  header: { height: 60, paddingHorizontal: 16, flexDirection: "row-reverse", justifyContent: "space-between", alignItems: "center", backgroundColor: "#FFF", borderBottomWidth: 1, borderColor: "#EEE" },
  headerBtn: { padding: 8 },
  title: { fontSize: 18, fontWeight: "900", color: "#111" },
  addSection: { backgroundColor: "#FFF", padding: 16, borderBottomWidth: 1, borderColor: "#EEE" },
  sectionTitle: { fontSize: 15, fontWeight: "800", color: "#111", textAlign: "right", marginBottom: 12 },
  inputRow: { flexDirection: "row-reverse", gap: 12 },
  input: { flex: 1, height: 48, borderWidth: 1, borderColor: "#E5E5E5", borderRadius: 10, paddingHorizontal: 14, fontSize: 14, textAlign: "right", backgroundColor: "#FAFAFA" },
  addBtn: { height: 48, paddingHorizontal: 24, backgroundColor: "#111", borderRadius: 10, justifyContent: "center", alignItems: "center" },
  addBtnDisabled: { backgroundColor: "#CCC" },
  addBtnText: { color: "#FFF", fontWeight: "800", fontSize: 14 },
  listContainer: { flex: 1, padding: 16 },
  listContent: { paddingBottom: 100, gap: 12 },
  categoryCard: { flexDirection: "row-reverse", alignItems: "center", backgroundColor: "#FFF", padding: 16, borderRadius: 12, borderWidth: 1, borderColor: "#EEE", gap: 12 },
  categoryName: { flex: 1, fontSize: 15, fontWeight: "700", color: "#333", textAlign: "right" },
  center: { flex: 1, justifyContent: "center", alignItems: "center", padding: 40 },
  emptyBox: { padding: 40, alignItems: "center" },
  emptyText: { color: "#999", fontSize: 14, fontWeight: "700" },
});
