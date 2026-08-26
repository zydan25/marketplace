import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import * as ImagePicker from "expo-image-picker";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, Image, Pressable, ScrollView, StyleSheet, Switch, Text, TextInput, View } from "react-native";

import { AdminLayout, Colors, Font, Radius, Shadow, Spacing } from "@/components/admin";
import { useAuth } from "@/hooks/use-auth";
import {
  createCircle,
  createSlide,
  deleteCircle,
  deleteSlide,
  deleteTab,
  getAdminStorefront,
  type StorefrontCircle,
  type StorefrontSlide,
  type StorefrontTab,
  updateCircle,
  updateSlide,
  updateTab,
} from "@/lib/storefront-api";
import { createAdvancedSection, getAdminCategories, type AdminCategory } from "@/lib/storefront-admin-api";
import { djangoApi } from "@/lib/django-api";

 type AdminServiceCategory = { id: number; name: string; parent: number | null; children_count?: number };
 type UploadedImage = { dataUrl: string; fileName: string };
 type SectionType = "hero" | "banner" | "category" | "product_grid" | "service_grid" | "trend";

async function pickImage(): Promise<UploadedImage | undefined> {
  const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], quality: 0.82, base64: true });
  if (result.canceled || !result.assets[0]?.base64) return undefined;
  const asset = result.assets[0];
  return { dataUrl: `data:${asset.mimeType ?? "image/jpeg"};base64,${asset.base64}`, fileName: asset.fileName ?? `storefront-${Date.now()}.jpg` };
}

const sectionTypes: { value: SectionType; label: string; icon: keyof typeof MaterialIcons.glyphMap }[] = [
  { value: "hero", label: "عرض رئيسي", icon: "view-carousel" },
  { value: "banner", label: "بانر", icon: "image" },
  { value: "category", label: "دوائر فئات", icon: "category" },
  { value: "product_grid", label: "شبكة منتجات", icon: "grid-view" },
  { value: "service_grid", label: "شبكة خدمات", icon: "miscellaneous-services" },
  { value: "trend", label: "ترند / بطاقات", icon: "trending-up" },
];

function Chip({ active, label, onPress }: { active: boolean; label: string; onPress: () => void }) {
  return <Pressable onPress={onPress} style={[styles.chip, active && styles.chipActive]}><Text style={[styles.chipText, active && styles.chipTextActive]}>{label}</Text></Pressable>;
}

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return <View style={styles.card}><Text style={styles.cardTitle}>{title}</Text>{children}</View>;
}

export default function StorefrontV2() {
  useAuth();
  const [tabs, setTabs] = useState<StorefrontTab[]>([]);
  const [categories, setCategories] = useState<AdminCategory[]>([]);
  const [serviceCategories, setServiceCategories] = useState<AdminServiceCategory[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [newTitle, setNewTitle] = useState("");
  const [newType, setNewType] = useState<SectionType>("product_grid");
  const [showCategoryCircles, setShowCategoryCircles] = useState(true);
  const [selectedCategoryIds, setSelectedCategoryIds] = useState<number[]>([]);
  const [selectedServiceCategoryIds, setSelectedServiceCategoryIds] = useState<number[]>([]);
  const [slideTitle, setSlideTitle] = useState("");
  const [slideSubtitle, setSlideSubtitle] = useState("");
  const [slideImage, setSlideImage] = useState<UploadedImage>();
  const [circleImage, setCircleImage] = useState<UploadedImage>();
  const [circleCategoryId, setCircleCategoryId] = useState<number | null>(null);

  const selected = useMemo(() => tabs.find((tab) => tab.id === selectedId) ?? null, [selectedId, tabs]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [nextTabs, nextCategories, nextServices] = await Promise.all([
        getAdminStorefront(),
        getAdminCategories(),
        djangoApi<{ results?: AdminServiceCategory[] } | AdminServiceCategory[]>("/api/service-categories/").then((data) => Array.isArray(data) ? data : (data.results ?? [])),
      ]);
      setTabs(nextTabs);
      setCategories(nextCategories);
      setServiceCategories(nextServices);
      setSelectedId((current) => current && nextTabs.some((tab) => tab.id === current) ? current : nextTabs[0]?.id ?? null);
    } catch (error) {
      Alert.alert("تعذر تحميل محرر الواجهة", error instanceof Error ? error.message : "حاول مرة أخرى.");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    const config = (selected?.config ?? {}) as Record<string, unknown>;
    const ids = Array.isArray(config.category_ids) ? config.category_ids.map(Number).filter(Number.isFinite) : [];
    const serviceIds = Array.isArray(config.service_category_ids) ? config.service_category_ids.map(Number).filter(Number.isFinite) : [];
    setShowCategoryCircles(config.showCategoryCircles !== false);
    setSelectedCategoryIds(ids);
    setSelectedServiceCategoryIds(serviceIds);
  }, [selectedId]);

  async function addSection() {
    if (!newTitle.trim()) { Alert.alert("بيانات ناقصة", "أدخل اسم القسم."); return; }
    setSaving(true);
    try {
      await createAdvancedSection({
        title: newTitle.trim(),
        sectionType: newType,
        config: newType === "product_grid" ? { source: "products", showCategoryCircles, category_ids: selectedCategoryIds } : newType === "service_grid" ? { source: "services", service_category_ids: selectedServiceCategoryIds } : newType === "category" ? { category_ids: selectedCategoryIds } : {},
      });
      setNewTitle("");
      await load();
    } catch (error) { Alert.alert("تعذر إنشاء القسم", error instanceof Error ? error.message : "حاول مرة أخرى."); } finally { setSaving(false); }
  }

  async function saveSelectedConfig(extra: Record<string, unknown> = {}) {
    if (!selected) return;
    const config = { ...(selected.config ?? {}), ...extra } as Record<string, unknown>;
    await updateTab(selected.id, { config });
    await load();
  }

  async function saveCategoryBinding() {
    if (!selected) return;
    setSaving(true);
    try {
      if (selected.type === "service_grid") {
        await saveSelectedConfig({ source: "services", service_category_ids: selectedServiceCategoryIds });
      } else if (selected.type === "category") {
        await saveSelectedConfig({ category_ids: selectedCategoryIds });
      } else {
        await saveSelectedConfig({ source: "products", showCategoryCircles, category_ids: selectedCategoryIds });
      }
    } catch (error) { Alert.alert("تعذر حفظ إعدادات القسم", error instanceof Error ? error.message : "حاول مرة أخرى."); } finally { setSaving(false); }
  }

  async function addSlideToSelected() {
    if (!selected || !slideImage) { Alert.alert("صورة مطلوبة", "اختر صورة للعرض أولًا."); return; }
    setSaving(true);
    try {
      const result = await createSlide(selected.id, { title: slideTitle.trim(), subtitle: slideSubtitle.trim(), ctaLabel: "تسوّق الآن", image: slideImage });
      setTabs(result.tabs);
      setSlideTitle(""); setSlideSubtitle(""); setSlideImage(undefined);
    } catch (error) { Alert.alert("تعذر حفظ العرض", error instanceof Error ? error.message : "حاول مرة أخرى."); } finally { setSaving(false); }
  }

  async function addCircleForCategory() {
    if (!selected || !circleCategoryId) { Alert.alert("اختر فئة", "اختر فئة من القائمة أولًا."); return; }
    const category = categories.find((item) => item.id === circleCategoryId);
    if (!category) return;
    setSaving(true);
    try {
      const result = await createCircle(selected.id, { title: category.name, targetCategory: category.slug, ...(circleImage ? { image: circleImage } : {}) });
      setTabs(result.tabs);
      setCircleCategoryId(null); setCircleImage(undefined);
    } catch (error) { Alert.alert("تعذر إضافة الفئة", error instanceof Error ? error.message : "حاول مرة أخرى."); } finally { setSaving(false); }
  }

  async function toggleSection() {
    if (!selected) return;
    await updateTab(selected.id, { isActive: !selected.isActive });
    await load();
  }

  async function removeSection() {
    if (!selected) return;
    Alert.alert("حذف القسم", `هل تريد حذف «${selected.title}»؟`, [
      { text: "إلغاء", style: "cancel" },
      { text: "حذف", style: "destructive", onPress: async () => { await deleteTab(selected.id); await load(); } },
    ]);
  }

  return <AdminLayout title="محرر واجهة المتجر v2">
    <ScrollView style={{ flex: 1 }} contentContainerStyle={styles.page} showsVerticalScrollIndicator={false}>
      <View style={styles.hero}>
        <View style={styles.heroIcon}><MaterialIcons name="dashboard-customize" size={26} color="#FFF" /></View>
        <View style={{ flex: 1 }}><Text style={styles.heroTitle}>تحكم ديناميكي كامل بالواجهة</Text><Text style={styles.heroText}>أنشئ أقسامًا، اختر فئات المنتجات أو الخدمات، ورتبها وفعّلها أو أخفها.</Text></View>
      </View>

      <SectionCard title="إنشاء قسم جديد">
        <TextInput value={newTitle} onChangeText={setNewTitle} placeholder="اسم القسم" placeholderTextColor="#999" style={styles.input} textAlign="right" />
        <Text style={styles.label}>نوع القسم</Text>
        <View style={styles.chipWrap}>{sectionTypes.map((item) => <Chip key={item.value} active={newType === item.value} label={item.label} onPress={() => setNewType(item.value)} />)}</View>
        {(newType === "product_grid" || newType === "category") && <>
          <Text style={styles.label}>فئات المنتجات</Text>
          <View style={styles.chipWrap}>{categories.map((category) => <Chip key={category.id} active={selectedCategoryIds.includes(category.id)} label={category.name} onPress={() => setSelectedCategoryIds((old) => old.includes(category.id) ? old.filter((id) => id !== category.id) : [...old, category.id])} />)}</View>
          {newType === "product_grid" && <View style={styles.switchRow}><Text style={styles.switchLabel}>إظهار دوائر الفئات داخل شبكة المنتجات</Text><Switch value={showCategoryCircles} onValueChange={setShowCategoryCircles} /></View>}
        </>}
        {newType === "service_grid" && <>
          <Text style={styles.label}>فئات الخدمات</Text>
          <View style={styles.chipWrap}>{serviceCategories.map((category) => <Chip key={category.id} active={selectedServiceCategoryIds.includes(category.id)} label={category.name} onPress={() => setSelectedServiceCategoryIds((old) => old.includes(category.id) ? old.filter((id) => id !== category.id) : [...old, category.id])} />)}</View>
        </>}
        <Pressable disabled={saving} onPress={addSection} style={styles.primary}><Text style={styles.primaryText}>{saving ? "جارٍ الحفظ..." : "إنشاء القسم"}</Text></Pressable>
      </SectionCard>

      <SectionCard title="أقسام الواجهة الحالية">
        {loading ? <Text style={styles.muted}>جارٍ التحميل...</Text> : tabs.length === 0 ? <Text style={styles.muted}>لا توجد أقسام.</Text> : <View style={styles.chipWrap}>{tabs.map((tab) => <Chip key={tab.id} active={selected?.id === tab.id} label={tab.title} onPress={() => setSelectedId(tab.id)} />)}</View>}
      </SectionCard>

      {selected && <>
        <SectionCard title={`تحرير: ${selected.title}`}>
          <View style={styles.switchRow}><Text style={styles.switchLabel}>إظهار القسم في المتجر</Text><Switch value={selected.isActive} onValueChange={toggleSection} /></View>
          <Text style={styles.meta}>النوع: {sectionTypes.find((item) => item.value === selected.type)?.label ?? selected.type}</Text>
          {(selected.type === "product_grid" || selected.type === "category") && <>
            <Text style={styles.label}>الفئات المرتبطة</Text>
            <View style={styles.chipWrap}>{categories.map((category) => <Chip key={category.id} active={selectedCategoryIds.includes(category.id)} label={category.name} onPress={() => setSelectedCategoryIds((old) => old.includes(category.id) ? old.filter((id) => id !== category.id) : [...old, category.id])} />)}</View>
            {selected.type === "product_grid" && <View style={styles.switchRow}><Text style={styles.switchLabel}>دوائر الفئات داخل الشبكة</Text><Switch value={showCategoryCircles} onValueChange={setShowCategoryCircles} /></View>}
            <Pressable disabled={saving} onPress={saveCategoryBinding} style={styles.secondary}><Text style={styles.secondaryText}>حفظ ربط الفئات</Text></Pressable>
          </>}
          {selected.type === "service_grid" && <>
            <Text style={styles.label}>فئات الخدمات المرتبطة</Text>
            <View style={styles.chipWrap}>{serviceCategories.map((category) => <Chip key={category.id} active={selectedServiceCategoryIds.includes(category.id)} label={category.name} onPress={() => setSelectedServiceCategoryIds((old) => old.includes(category.id) ? old.filter((id) => id !== category.id) : [...old, category.id])} />)}</View>
            <Pressable disabled={saving} onPress={saveCategoryBinding} style={styles.secondary}><Text style={styles.secondaryText}>حفظ خدمات القسم</Text></Pressable>
          </>}
          <Pressable onPress={removeSection} style={styles.delete}><MaterialIcons name="delete-outline" size={18} color={Colors.danger} /><Text style={styles.deleteText}>حذف القسم</Text></Pressable>
        </SectionCard>

        {(selected.type === "hero" || selected.type === "banner") && <SectionCard title="عروض الصور">
          <TextInput value={slideTitle} onChangeText={setSlideTitle} placeholder="العنوان" placeholderTextColor="#999" style={styles.input} textAlign="right" />
          <TextInput value={slideSubtitle} onChangeText={setSlideSubtitle} placeholder="الوصف" placeholderTextColor="#999" style={[styles.input, { marginTop: 8 }]} textAlign="right" />
          <Pressable onPress={async () => { const image = await pickImage(); if (image) setSlideImage(image); }} style={styles.imagePicker}>{slideImage ? <Image source={{ uri: slideImage.dataUrl }} style={styles.image} /> : <View style={styles.imageEmpty}><MaterialIcons name="add-photo-alternate" size={24} color="#888" /><Text style={styles.muted}>اختيار صورة</Text></View>}</Pressable>
          <Pressable disabled={saving} onPress={addSlideToSelected} style={styles.primary}><Text style={styles.primaryText}>إضافة العرض</Text></Pressable>
          <VisualItems items={selected.slides} onToggle={async (id, active) => { await updateSlide(id, { isActive: active }); await load(); }} onDelete={async (id) => { await deleteSlide(id); await load(); }} />
        </SectionCard>}

        {selected.type === "category" && <SectionCard title="إضافة فئة كأيقونة دائرية">
          <Text style={styles.label}>اختيار الفئة</Text>
          <View style={styles.chipWrap}>{categories.map((category) => <Chip key={category.id} active={circleCategoryId === category.id} label={category.name} onPress={() => setCircleCategoryId(category.id)} />)}</View>
          <Pressable onPress={async () => { const image = await pickImage(); if (image) setCircleImage(image); }} style={styles.imagePicker}>{circleImage ? <Image source={{ uri: circleImage.dataUrl }} style={styles.image} /> : <View style={styles.imageEmpty}><MaterialIcons name="add-photo-alternate" size={24} color="#888" /><Text style={styles.muted}>صورة اختيارية</Text></View>}</Pressable>
          <Pressable disabled={saving} onPress={addCircleForCategory} style={styles.primary}><Text style={styles.primaryText}>إضافة الفئة</Text></Pressable>
          <VisualItems items={selected.circles} onToggle={async (id, active) => { await updateCircle(id, { isActive: active }); await load(); }} onDelete={async (id) => { await deleteCircle(id); await load(); }} circle />
        </SectionCard>}
      </>}
    </ScrollView>
  </AdminLayout>;
}

function VisualItems({ items, onToggle, onDelete, circle }: { items: (StorefrontSlide | StorefrontCircle)[]; onToggle: (id: string, active: boolean) => void; onDelete: (id: string) => void; circle?: boolean }) {
  if (!items.length) return <Text style={styles.muted}>لا توجد عناصر بعد.</Text>;
  return <View style={{ marginTop: 12 }}>{items.map((item) => <View key={item.id} style={styles.visualRow}>
    {item.imageUrl ? <Image source={{ uri: item.imageUrl }} style={[styles.visualImage, circle && styles.visualCircle]} /> : <View style={[styles.visualImage, styles.imageEmpty, circle && styles.visualCircle]}><MaterialIcons name="image" size={18} color="#888" /></View>}
    <View style={{ flex: 1 }}><Text style={styles.visualTitle}>{item.title}</Text><Text style={styles.meta}>{circle ? `الفئة: ${(item as StorefrontCircle).targetCategory}` : (item as StorefrontSlide).subtitle}</Text></View>
    <Switch value={item.isActive} onValueChange={(v) => onToggle(item.id, v)} />
    <Pressable onPress={() => onDelete(item.id)}><MaterialIcons name="delete-outline" size={20} color={Colors.danger} /></Pressable>
  </View>)}</View>;
}

const styles = StyleSheet.create({
  page: { padding: 16, paddingBottom: 60, backgroundColor: "#F6F6F7" },
  hero: { flexDirection: "row-reverse", gap: 12, padding: 18, borderRadius: 18, backgroundColor: Colors.black, marginBottom: 14 },
  heroIcon: { width: 48, height: 48, borderRadius: 14, backgroundColor: Colors.primary, alignItems: "center", justifyContent: "center" },
  heroTitle: { color: "#FFF", fontSize: 18, fontWeight: "900", textAlign: "right" },
  heroText: { color: "#B8B8BE", fontSize: 11, lineHeight: 18, textAlign: "right", marginTop: 5 },
  card: { backgroundColor: "#FFF", borderRadius: 16, padding: 16, marginBottom: 12, ...Shadow.soft },
  cardTitle: { fontSize: 15, fontWeight: "900", color: "#111", textAlign: "right", marginBottom: 12 },
  input: { height: 46, borderWidth: 1, borderColor: "#E4E4E7", backgroundColor: "#FAFAFA", borderRadius: 11, paddingHorizontal: 12, color: "#111", fontSize: 13 },
  label: { fontSize: 11, fontWeight: "800", color: "#333", textAlign: "right", marginTop: 12, marginBottom: 8 },
  chipWrap: { flexDirection: "row-reverse", flexWrap: "wrap", gap: 8 },
  chip: { paddingHorizontal: 11, paddingVertical: 8, borderRadius: 18, backgroundColor: "#FFF", borderWidth: 1, borderColor: "#E2E2E6" },
  chipActive: { backgroundColor: "#111", borderColor: "#111" },
  chipText: { fontSize: 10, color: "#555" },
  chipTextActive: { color: "#FFF", fontWeight: "800" },
  switchRow: { flexDirection: "row-reverse", justifyContent: "space-between", alignItems: "center", marginTop: 12 },
  switchLabel: { flex: 1, fontSize: 11, color: "#333", textAlign: "right", marginRight: 10 },
  primary: { height: 46, backgroundColor: Colors.primary, borderRadius: 12, alignItems: "center", justifyContent: "center", marginTop: 14 },
  primaryText: { color: "#FFF", fontSize: 12, fontWeight: "900" },
  secondary: { height: 44, backgroundColor: "#111", borderRadius: 12, alignItems: "center", justifyContent: "center", marginTop: 12 },
  secondaryText: { color: "#FFF", fontSize: 11, fontWeight: "900" },
  delete: { marginTop: 14, paddingVertical: 10, alignItems: "center", flexDirection: "row-reverse", justifyContent: "center", gap: 5 },
  deleteText: { color: Colors.danger, fontWeight: "800", fontSize: 11 },
  imagePicker: { height: 110, borderWidth: 2, borderStyle: "dashed", borderColor: "#DDD", borderRadius: 12, overflow: "hidden", marginTop: 12 },
  image: { width: "100%", height: "100%" },
  imageEmpty: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: "#FAFAFA", gap: 6 },
  visualRow: { flexDirection: "row-reverse", alignItems: "center", gap: 10, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: "#E8E8E8", paddingVertical: 10 },
  visualImage: { width: 52, height: 52, borderRadius: 10, backgroundColor: "#F5F5F5" },
  visualCircle: { borderRadius: 26 },
  visualTitle: { fontSize: 12, fontWeight: "900", color: "#111", textAlign: "right" },
  meta: { fontSize: 9, color: "#888", textAlign: "right", marginTop: 3 },
  muted: { color: "#888", fontSize: 10, textAlign: "right", marginTop: 5 },
});
