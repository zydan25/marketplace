import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { useCallback, useEffect, useState } from "react";
import { Alert, ActivityIndicator, FlatList, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";

import { ScreenContainer } from "@/components/screen-container";
import { useAuth } from "@/hooks/use-auth";
import { ApiClient } from "@/lib/api-client";
import type { StoreCategory } from "@/lib/category-api";

export default function AdminCategoriesScreen() {
  const { user, isAuthenticated } = useAuth();
  const [categories, setCategories] = useState<StoreCategory[]>([]);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const load = useCallback(async () => {
    try {
      setLoading(true);
      const response = await ApiClient.get<{ results?: StoreCategory[] } | StoreCategory[]>("/api/categories/");
      setCategories(Array.isArray(response) ? response : (response.results ?? []));
    } catch (error) {
      Alert.alert("تعذر تحميل الفئات", error instanceof Error ? error.message : "حاولي مجددًا.");
    } finally { setLoading(false); }
  }, []);
  useEffect(() => { if (isAuthenticated && user?.role === "admin") load(); }, [isAuthenticated, user?.role, load]);
  async function addCategory() {
    const title = name.trim();
    if (!title) { Alert.alert("اسم الفئة مطلوب", "اكتبي اسم الفئة قبل الحفظ."); return; }
    try {
      setSaving(true);
      const slug = title.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, "-").replace(/^-|-$/g, "") || `category-${Date.now()}`;
      const created = await ApiClient.post<StoreCategory>("/api/categories/", { name: title, slug, is_active: true, sort_order: categories.length });
      setCategories((items) => [...items, created]);
      setName("");
      Alert.alert("تمت الإضافة", `أضيفت فئة «${title}» ويمكن اختيارها عند إضافة الصنف.`);
    } catch (error) { Alert.alert("تعذر إضافة الفئة", error instanceof Error ? error.message : "راجعي البيانات وحاولي مرة أخرى."); }
    finally { setSaving(false); }
  }
  if (!isAuthenticated || user?.role !== "admin") return <ScreenContainer edges={["top", "bottom", "left", "right"]} className="bg-white"><View style={styles.center}><MaterialIcons name="lock-outline" size={38} color="#E60023" /><Text style={styles.title}>هذه الصفحة للمدير فقط</Text></View></ScreenContainer>;
  return <ScreenContainer edges={["top", "bottom", "left", "right"]} className="bg-[#F6F6F6]"><View style={styles.header}><TouchableOpacity onPress={() => router.back()}><MaterialIcons name="arrow-forward" size={24} color="#171717" /></TouchableOpacity><Text style={styles.headerTitle}>إدارة الفئات</Text><TouchableOpacity onPress={load}><MaterialIcons name="refresh" size={22} color="#E60023" /></TouchableOpacity></View><View style={styles.form}><Text style={styles.hint}>أضيفي الفئة مرة واحدة، وستظهر تلقائيًا في الصفحة الرئيسية واختيار فئات الصنف.</Text><View style={styles.inputRow}><TouchableOpacity style={styles.addButton} disabled={saving} onPress={addCategory}><Text style={styles.addText}>{saving ? "..." : "إضافة"}</Text></TouchableOpacity><TextInput value={name} onChangeText={setName} placeholder="اسم الفئة، مثال: أزياء" placeholderTextColor="#999" textAlign="right" style={styles.input} /></View></View><FlatList style={{ flex: 1 }} data={categories} keyExtractor={(item) => String(item.id)} contentContainerStyle={styles.list} refreshing={loading} onRefresh={load} ListEmptyComponent={loading ? <ActivityIndicator color="#E60023" /> : <Text style={styles.empty}>لا توجد فئات بعد.</Text>} renderItem={({ item }) => <View style={styles.card}><View style={styles.icon}><MaterialIcons name="category" size={23} color="#E60023" /></View><View style={styles.copy}><Text style={styles.name}>{item.name}</Text><Text style={styles.meta}>{item.slug} · {item.is_active === false ? "غير مفعلة" : "مفعلة"}</Text></View><TouchableOpacity onPress={async () => { try { const updated = await ApiClient.patch<StoreCategory>(`/api/categories/${item.id}/`, { is_active: item.is_active === false }); setCategories((items) => items.map((category) => category.id === item.id ? updated : category)); } catch (error) { Alert.alert("تعذر التحديث", error instanceof Error ? error.message : "حاولي مجددًا."); } }}><Text style={styles.toggle}>{item.is_active === false ? "تفعيل" : "إيقاف"}</Text></TouchableOpacity></View>} /></ScreenContainer>;
}

const styles = StyleSheet.create({ header: { height: 57, backgroundColor: "#FFFFFF", paddingHorizontal: 15, flexDirection: "row", alignItems: "center", justifyContent: "space-between", borderBottomWidth: 1, borderColor: "#E8E8E8" }, headerTitle: { color: "#171717", fontSize: 16, fontWeight: "900" }, form: { backgroundColor: "#FFFFFF", padding: 14 }, hint: { color: "#777", fontSize: 11, lineHeight: 18, textAlign: "right", marginBottom: 12 }, inputRow: { flexDirection: "row-reverse", gap: 8 }, input: { flex: 1, height: 46, backgroundColor: "#F5F5F5", paddingHorizontal: 12, color: "#171717", borderWidth: 1, borderColor: "#E5E5E5" }, addButton: { width: 72, height: 46, backgroundColor: "#E60023", alignItems: "center", justifyContent: "center" }, addText: { color: "#FFF", fontWeight: "900" }, list: { padding: 12, paddingBottom: 180 }, card: { minHeight: 68, backgroundColor: "#FFF", padding: 12, marginBottom: 8, flexDirection: "row-reverse", alignItems: "center", gap: 10 }, icon: { width: 42, height: 42, alignItems: "center", justifyContent: "center", backgroundColor: "#FFF2F3" }, copy: { flex: 1, alignItems: "flex-end" }, name: { color: "#171717", fontSize: 14, fontWeight: "900" }, meta: { color: "#888", fontSize: 10, marginTop: 4 }, toggle: { color: "#E60023", fontSize: 11, fontWeight: "800" }, empty: { textAlign: "center", color: "#777", marginTop: 50 }, center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12 }, title: { color: "#171717", fontSize: 18, fontWeight: "900" } });
