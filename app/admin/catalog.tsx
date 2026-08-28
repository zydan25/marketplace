import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Alert, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import { AdminLayout, Colors, Font, Radius, Spacing } from "@/components/admin";
import { apiCall } from "@/lib/_core/api";

type Node = { id: number; name: string; slug: string; parent?: number | null; children?: Node[]; is_active?: boolean };
type Option = { id: number; group: string; name: string; slug: string; category?: number | null; category_name?: string | null; is_active?: boolean };
const GROUPS = ["condition", "warranty", "gender", "material", "brand"];

export default function AdminCatalogScreen() {
  const [tree, setTree] = useState<Node[]>([]);
  const [options, setOptions] = useState<Record<string, Option[]>>({});
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [parent, setParent] = useState<number | null>(null);
  const [group, setGroup] = useState("condition");
  const [optName, setOptName] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiCall<{ categories: Node[]; options: Record<string, Option[]> }>("/api/catalog/tree/");
      setTree(data.categories ?? []);
      setOptions(data.options ?? {});
    } catch (error) {
      Alert.alert("تعذر تحميل التصنيفات", error instanceof Error ? error.message : "حاول مجددًا.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function addCategory() {
    const title = name.trim();
    if (!title) return Alert.alert("اسم الفئة مطلوب", "اكتب اسم الفئة.");
    try {
      setBusy(true);
      const slug = `${title.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, "-")}-${Date.now()}`;
      await apiCall("/api/categories/", { method: "POST", body: JSON.stringify({ name: title, slug, parent, is_active: true, sort_order: 0 }) });
      setName(""); setParent(null); await load();
    } catch (error) {
      Alert.alert("تعذر الإضافة", error instanceof Error ? error.message : "قد يكون الاسم موجودًا بالفعل.");
    } finally { setBusy(false); }
  }

  async function addOption() {
    const title = optName.trim();
    if (!title) return Alert.alert("القيمة مطلوبة", "اكتب القيمة.");
    try {
      setBusy(true);
      const option = await apiCall<Option>("/api/catalog-options/", { method: "POST", body: JSON.stringify({ group, name: title, is_active: true }) });
      setOptions((current) => ({ ...current, [group]: [...(current[group] ?? []), option] })); setOptName("");
    } catch (error) {
      Alert.alert("تعذر إضافة القيمة", error instanceof Error ? error.message : "حاول مجددًا.");
    } finally { setBusy(false); }
  }

  async function toggleCategory(item: Node) {
    try {
      await apiCall(`/api/categories/${item.id}/`, { method: "PATCH", body: JSON.stringify({ is_active: item.is_active === false }) });
      await load();
    } catch (error) {
      Alert.alert("تعذر التحديث", error instanceof Error ? error.message : "حاول مجددًا.");
    }
  }

  return (
    <AdminLayout title="كتالوج المنصة">
      <ScrollView contentContainerStyle={styles.page}>
        <View style={styles.back}><TouchableOpacity onPress={() => router.back()}><MaterialIcons name="arrow-forward" size={22} color="#111" /></TouchableOpacity></View>
        <View style={styles.card}>
          <Text style={styles.heading}>الفئات العامة والخاصة</Text>
          <Text style={styles.help}>أضف فئة عامة، ثم اخترها لإضافة فئة فرعية. هذه البيانات تظهر للتاجر عند إنشاء المنتج.</Text>
          <Text style={styles.label}>الفئة الأب</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
            <TouchableOpacity onPress={() => setParent(null)} style={[styles.chip, parent === null && styles.activeChip]}><Text style={parent === null ? styles.activeText : styles.chipText}>جذر</Text></TouchableOpacity>
            {tree.map((item) => <TouchableOpacity key={item.id} onPress={() => setParent(item.id)} style={[styles.chip, parent === item.id && styles.activeChip]}><Text style={parent === item.id ? styles.activeText : styles.chipText}>{item.name}</Text></TouchableOpacity>)}
          </ScrollView>
          <View style={styles.row}><TextInput value={name} onChangeText={setName} placeholder="اسم الفئة الجديدة" placeholderTextColor="#999" style={styles.input} textAlign="right" /><TouchableOpacity disabled={busy} onPress={addCategory} style={styles.addButton}><Text style={styles.addText}>إضافة</Text></TouchableOpacity></View>
        </View>
        <View style={styles.card}>
          <Text style={styles.heading}>خيارات المنتجات</Text>
          <Text style={styles.help}>القيم العامة مثل الحالة والضمان والخامة والشركات. يمكن تعديلها أو تعطيلها من الإدارة.</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>{GROUPS.map((item) => <TouchableOpacity key={item} onPress={() => setGroup(item)} style={[styles.chip, group === item && styles.activeChip]}><Text style={group === item ? styles.activeText : styles.chipText}>{item}</Text></TouchableOpacity>)}</ScrollView>
          <View style={styles.row}><TextInput value={optName} onChangeText={setOptName} placeholder="قيمة جديدة" placeholderTextColor="#999" style={styles.input} textAlign="right" /><TouchableOpacity disabled={busy} onPress={addOption} style={styles.addButton}><Text style={styles.addText}>إضافة</Text></TouchableOpacity></View>
          {(options[group] ?? []).map((item) => <View key={item.id} style={styles.item}><Text style={styles.itemMeta}>{item.is_active === false ? "متوقف" : "مفعل"}</Text><Text style={styles.itemName}>{item.name}</Text></View>)}
        </View>
        <View style={styles.card}>
          <Text style={styles.heading}>هيكل التصنيف</Text>
          {loading ? <ActivityIndicator color={Colors.primary} /> : tree.map((root) => (
            <View key={root.id} style={styles.root}>
              <View style={styles.rootRow}><TouchableOpacity onPress={() => toggleCategory(root)}><Text style={styles.toggle}>{root.is_active === false ? "تفعيل" : "إيقاف"}</Text></TouchableOpacity><Text style={styles.rootName}>{root.name}</Text></View>
              {(root.children ?? []).map((child) => <Text key={child.id} style={styles.child}>↳ {child.name}</Text>)}
            </View>
          ))}
        </View>
      </ScrollView>
    </AdminLayout>
  );
}

const styles = StyleSheet.create({
  page: { paddingBottom: 100 }, back: { paddingHorizontal: Spacing.lg, paddingTop: Spacing.md }, card: { marginHorizontal: Spacing.lg, marginTop: Spacing.sm, backgroundColor: Colors.surface, borderRadius: Radius.md, padding: Spacing.lg },
  heading: { color: Colors.text, ...Font.sectionTitle, textAlign: "right" }, help: { color: Colors.textSecondary, ...Font.small, textAlign: "right", lineHeight: 18, marginTop: 5 }, label: { color: Colors.text, ...Font.small, textAlign: "right", marginTop: 12, marginBottom: 5 },
  chips: { flexDirection: "row-reverse", flexWrap: "wrap", gap: 7, marginBottom: 10 }, chip: { paddingHorizontal: 11, paddingVertical: 8, borderRadius: 17, borderWidth: 1, borderColor: Colors.divider }, activeChip: { backgroundColor: Colors.black, borderColor: Colors.black }, chipText: { color: Colors.textSecondary, fontSize: 10, fontWeight: "700" }, activeText: { color: Colors.textInverse, fontSize: 10, fontWeight: "800" },
  row: { flexDirection: "row-reverse", gap: 8, alignItems: "center" }, input: { flex: 1, height: 45, borderWidth: 1, borderColor: Colors.divider, borderRadius: 9, paddingHorizontal: 12, color: Colors.text, backgroundColor: Colors.surfaceAlt }, addButton: { height: 45, minWidth: 70, backgroundColor: Colors.primary, borderRadius: 9, alignItems: "center", justifyContent: "center" }, addText: { color: Colors.textInverse, fontWeight: "900", fontSize: 11 },
  item: { paddingVertical: 9, borderBottomWidth: 1, borderColor: Colors.divider, flexDirection: "row-reverse", justifyContent: "space-between" }, itemName: { color: Colors.text, fontWeight: "700", fontSize: 12 }, itemMeta: { color: Colors.success, fontSize: 9 }, root: { paddingVertical: 8, borderBottomWidth: 1, borderColor: Colors.divider }, rootRow: { flexDirection: "row-reverse", justifyContent: "space-between", alignItems: "center" }, rootName: { fontSize: 13, fontWeight: "900", color: Colors.text }, toggle: { fontSize: 9, color: Colors.primary, fontWeight: "800" }, child: { paddingVertical: 5, paddingRight: 10, fontSize: 11, color: Colors.textSecondary },
});
