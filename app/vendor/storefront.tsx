import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import * as ImagePicker from "expo-image-picker";
import { useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Alert, Image, ScrollView, StyleSheet, Switch, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";

import { ScreenContainer } from "@/components/screen-container";
import { djangoApi } from "@/lib/django-api";

const TYPES = [
  { id: "hero", label: "الرئيسية", icon: "view-carousel" },
  { id: "banner", label: "بانر", icon: "image" },
  { id: "category", label: "الفئات", icon: "category" },
  { id: "product_grid", label: "شبكة منتجات", icon: "grid-view" },
  { id: "trend", label: "الترند", icon: "trending-up" },
] as const;
type SectionType = typeof TYPES[number]["id"];
type Section = { id: number; title: string; section_type: SectionType; config: Record<string, any>; sort_order: number; is_visible: boolean };
type Category = { id: number; name: string; slug: string; parent?: number | null; is_active?: boolean };
type Draft = { title: string; type: SectionType; subtitle: string; imageUrl: string; button: string; url: string; visible: boolean; source: "latest" | "trending" | "category"; categoryId: string; rows: string; columns: string; scroll: boolean };

const EMPTY: Draft = { title: "قسم جديد", type: "banner", subtitle: "", imageUrl: "", button: "", url: "", visible: true, source: "latest", categoryId: "", rows: "2", columns: "2", scroll: true };

export default function VendorStorefrontScreen() {
  const [sections, setSections] = useState<Section[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  async function load() {
    try {
      setLoading(true);
      const [sectionData, categoryData] = await Promise.all([
        djangoApi<{ results?: Section[] }>("/api/storefront-sections/"),
        djangoApi<{ results?: Category[] }>("/api/categories/"),
      ]);
      const next = (sectionData.results ?? []).sort((a, b) => a.sort_order - b.sort_order);
      setSections(next);
      setCategories(categoryData.results ?? []);
      if (selected && next.some((item) => item.id === selected)) edit(next.find((item) => item.id === selected)!);
    } catch (error) {
      Alert.alert("تعذر تحميل المحرر", error instanceof Error ? error.message : "حدث خطأ");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  function edit(section: Section) {
    const c = section.config ?? {};
    setSelected(section.id);
    setDraft({
      title: section.title || "",
      type: section.section_type,
      subtitle: String(c.subtitle ?? c.slides?.[0]?.subtitle ?? ""),
      imageUrl: String(c.image_url ?? c.imageUrl ?? c.slides?.[0]?.imageUrl ?? ""),
      button: String(c.button_label ?? c.slides?.[0]?.ctaLabel ?? ""),
      url: String(c.target_url ?? c.url ?? c.slides?.[0]?.url ?? ""),
      visible: section.is_visible,
      source: c.source === "trending" ? "trending" : c.source === "category" ? "category" : "latest",
      categoryId: String(c.category_id ?? ""),
      rows: String(c.rows ?? 2),
      columns: String(c.columns ?? 2),
      scroll: c.scroll !== false,
    });
  }

  async function create(type: SectionType = "banner") {
    try {
      const created = await djangoApi<Section>("/api/storefront-sections/", { method: "POST", body: JSON.stringify({ title: type === "product_grid" ? "منتجات مختارة" : type === "category" ? "الفئات" : "عرض جديد", section_type: type, config: type === "category" ? { published: true } : type === "product_grid" || type === "trend" ? { source: type === "trend" ? "trending" : "latest", rows: 2, columns: 2, scroll: true, published: true } : { slides: [], published: true }, sort_order: sections.length, is_visible: true }) });
      setSections((current) => [...current, created].sort((a, b) => a.sort_order - b.sort_order));
      edit(created);
    } catch (error) {
      Alert.alert("تعذر إنشاء القسم", error instanceof Error ? error.message : "حدث خطأ");
    }
  }

  async function pickImage() {
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], allowsEditing: true, quality: 0.82, base64: true });
    const asset = result.assets?.[0];
    if (!result.canceled && asset?.base64) setDraft((value) => ({ ...value, imageUrl: `data:${asset.mimeType ?? "image/jpeg"};base64,${asset.base64}` }));
  }

  async function save() {
    if (selected == null) return;
    const current = sections.find((item) => item.id === selected);
    const previous = current?.config ?? {};
    const config: Record<string, any> = { ...previous, published: true };
    if (draft.type === "category") {
      // Categories are platform-controlled; the vendor only controls the position/visibility of this block.
      delete config.categoryNames;
      delete config.categories;
      config.mode = "automatic";
    } else if (draft.type === "product_grid" || draft.type === "trend") {
      config.source = draft.type === "trend" ? "trending" : draft.source;
      config.category_id = draft.source === "category" ? (draft.categoryId ? Number(draft.categoryId) : null) : null;
      config.rows = Math.max(1, Math.min(6, Number(draft.rows) || 2));
      config.columns = Math.max(2, Math.min(4, Number(draft.columns) || 2));
      config.scroll = draft.scroll;
      config.subtitle = draft.subtitle;
      delete config.image_url;
      delete config.slides;
    } else {
      config.subtitle = draft.subtitle;
      config.image_url = draft.imageUrl;
      config.button_label = draft.button;
      config.target_url = draft.url;
      config.slides = draft.imageUrl ? [{ id: `${selected}-slide`, title: draft.title, subtitle: draft.subtitle, ctaLabel: draft.button || "تسوّق الآن", url: draft.url || "", imageUrl: draft.imageUrl, visible: true, isActive: true, sortOrder: 0 }] : [];
    }
    try {
      setSaving(true);
      const updated = await djangoApi<Section>(`/api/storefront-sections/${selected}/`, { method: "PATCH", body: JSON.stringify({ title: draft.title, section_type: draft.type, config, is_visible: draft.visible }) });
      setSections((items) => items.map((item) => item.id === updated.id ? updated : item).sort((a, b) => a.sort_order - b.sort_order));
      Alert.alert("تم الحفظ", "تم نشر إعدادات المتجر وسيظهر التصميم للعميل من صفحة المتجر.");
    } catch (error) {
      Alert.alert("تعذر حفظ التصميم", error instanceof Error ? error.message : "تحقق من البيانات.");
    } finally {
      setSaving(false);
    }
  }

  async function move(id: number, direction: -1 | 1) {
    const ordered = [...sections].sort((a, b) => a.sort_order - b.sort_order);
    const index = ordered.findIndex((item) => item.id === id);
    const target = index + direction;
    if (index < 0 || target < 0 || target >= ordered.length) return;
    [ordered[index], ordered[target]] = [ordered[target], ordered[index]];
    try {
      for (let i = 0; i < ordered.length; i += 1) await djangoApi(`/api/storefront-sections/${ordered[i].id}/`, { method: "PATCH", body: JSON.stringify({ sort_order: i }) });
      setSections(ordered.map((item, i) => ({ ...item, sort_order: i })));
    } catch { Alert.alert("تعذر الترتيب", "حاول مرة أخرى."); }
  }

  const current = useMemo(() => sections.find((item) => item.id === selected), [sections, selected]);

  if (loading) return <ScreenContainer><View style={styles.center}><ActivityIndicator color="#E60023" /><Text style={styles.muted}>جارٍ تحميل محرر المتجر...</Text></View></ScreenContainer>;

  return <ScreenContainer className="bg-[#F5F6F8]" edges={["top", "bottom", "left", "right"]}>
    <View style={styles.header}><TouchableOpacity onPress={() => router.back()}><MaterialIcons name="arrow-forward" size={24} color="#111" /></TouchableOpacity><View style={styles.headerCopy}><Text style={styles.headerTitle}>محرر واجهة المتجر</Text><Text style={styles.headerSub}>رتّب العرض، واترك الفئات للمنصة</Text></View><TouchableOpacity style={styles.headerAdd} onPress={() => create("product_grid")}><MaterialIcons name="add" size={24} color="#FFF" /></TouchableOpacity></View>
    <ScrollView style={{ flex: 1 }} contentContainerStyle={styles.page} keyboardShouldPersistTaps="handled">
      <View style={styles.quickAdd}><Text style={styles.quickTitle}>إضافة قسم</Text><ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.quickRow}>{TYPES.map((type) => <TouchableOpacity key={type.id} onPress={() => create(type.id)} style={styles.quickButton}><MaterialIcons name={type.icon as any} size={18} color="#111" /><Text style={styles.quickText}>{type.label}</Text></TouchableOpacity>)}</ScrollView></View>
      <View style={styles.previewCard}><Text style={styles.previewTitle}>معاينة مختصرة</Text>{sections.filter((s) => s.is_visible).map((section) => <Preview key={section.id} section={section} />)}{!sections.length ? <View style={styles.previewEmpty}><MaterialIcons name="dashboard-customize" size={36} color="#BBB" /><Text style={styles.muted}>ابدأ بإضافة بانر أو شبكة منتجات.</Text></View> : null}</View>
      <Text style={styles.sectionHeading}>ترتيب أقسام المتجر</Text>
      {sections.map((section, index) => <View key={section.id} style={[styles.sectionCard, selected === section.id && styles.selected]}>
        <TouchableOpacity style={styles.sectionTop} onPress={() => edit(section)}><View style={[styles.typeIcon, { backgroundColor: section.is_visible ? "#F0F8F3" : "#F1F1F1" }]}><MaterialIcons name={(TYPES.find((x) => x.id === section.section_type)?.icon ?? "view-module") as any} size={20} color={section.is_visible ? "#168451" : "#777"} /></View><View style={styles.sectionCopy}><Text style={styles.sectionTitle}>{section.title || "قسم بدون عنوان"}</Text><Text style={styles.sectionMeta}>{TYPES.find((x) => x.id === section.section_type)?.label ?? section.section_type} · الموضع {index + 1}</Text></View><MaterialIcons name="drag-handle" size={22} color="#B8B8B8" /></TouchableOpacity>
        <View style={styles.sectionActions}><TouchableOpacity style={styles.iconButton} disabled={index === 0} onPress={() => move(section.id, -1)}><MaterialIcons name="keyboard-arrow-up" size={21} color={index === 0 ? "#DDD" : "#333"} /></TouchableOpacity><TouchableOpacity style={styles.iconButton} disabled={index === sections.length - 1} onPress={() => move(section.id, 1)}><MaterialIcons name="keyboard-arrow-down" size={21} color={index === sections.length - 1 ? "#DDD" : "#333"} /></TouchableOpacity><Switch value={section.is_visible} onValueChange={async (value) => { await djangoApi(`/api/storefront-sections/${section.id}/`, { method: "PATCH", body: JSON.stringify({ is_visible: value }) }); setSections((items) => items.map((item) => item.id === section.id ? { ...item, is_visible: value } : item)); }} trackColor={{ true: "#168451" }} /><Text style={styles.smallLabel}>ظاهر</Text></View>
      </View>)}

      {current ? <View style={styles.editorCard}><Text style={styles.editorTitle}>تحرير: {current.title || "القسم"}</Text><TextInput value={draft.title} onChangeText={(value) => setDraft((d) => ({ ...d, title: value }))} style={styles.input} placeholder="عنوان القسم" textAlign="right" />
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.typeRow}>{TYPES.map((type) => <TouchableOpacity key={type.id} onPress={() => setDraft((d) => ({ ...d, type: type.id }))} style={[styles.typeButton, draft.type === type.id && styles.typeButtonActive]}><Text style={[styles.typeButtonText, draft.type === type.id && styles.typeButtonTextActive]}>{type.label}</Text></TouchableOpacity>)}</ScrollView>
        {draft.type === "category" ? <View style={styles.infoBox}><MaterialIcons name="category" size={20} color="#168451" /><Text style={styles.infoText}>الفئات العامة تضاف وتدار من المنصة تلقائيًا. من هنا تتحكم فقط في ظهور بلوك الفئات وموقعه داخل المتجر.</Text></View> : null}
        {(draft.type === "hero" || draft.type === "banner") ? <><TouchableOpacity onPress={pickImage} style={styles.mediaButton}><MaterialIcons name="add-photo-alternate" size={22} color="#E60023" /><Text style={styles.mediaText}>{draft.imageUrl.startsWith("data:") ? "تم اختيار صورة جديدة" : draft.imageUrl ? "تغيير صورة البانر" : "اختيار صورة البانر"}</Text></TouchableOpacity>{draft.imageUrl ? <Image source={{ uri: draft.imageUrl }} style={styles.editorImage} /> : null}<TextInput value={draft.subtitle} onChangeText={(value) => setDraft((d) => ({ ...d, subtitle: value }))} style={[styles.input, styles.multiline]} placeholder="وصف مختصر" multiline textAlign="right" /><TextInput value={draft.button} onChangeText={(value) => setDraft((d) => ({ ...d, button: value }))} style={styles.input} placeholder="نص الزر" textAlign="right" /><TextInput value={draft.url} onChangeText={(value) => setDraft((d) => ({ ...d, url: value }))} style={styles.input} placeholder="الرابط /collection?..." textAlign="left" autoCapitalize="none" /></> : null}
        {(draft.type === "product_grid" || draft.type === "trend") ? <><Text style={styles.fieldTitle}>مصدر المنتجات</Text><ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.typeRow}>{[{ value: "latest" as const, label: "الأحدث" }, { value: "trending" as const, label: "الأكثر مبيعًا / ترند" }, { value: "category" as const, label: "حسب فئة" }].map((item) => <TouchableOpacity key={item.value} disabled={draft.type === "trend"} onPress={() => setDraft((d) => ({ ...d, source: item.value }))} style={[styles.typeButton, (draft.type === "trend" ? item.value === "trending" : draft.source === item.value) && styles.typeButtonActive]}><Text style={[styles.typeButtonText, ((draft.type === "trend" ? item.value === "trending" : draft.source === item.value)) && styles.typeButtonTextActive]}>{item.label}</Text></TouchableOpacity>)}</ScrollView>{draft.source === "category" && draft.type !== "trend" ? <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.categoryRow}>{categories.map((category) => <TouchableOpacity key={category.id} onPress={() => setDraft((d) => ({ ...d, categoryId: String(category.id) }))} style={[styles.categoryChip, draft.categoryId === String(category.id) && styles.categoryChipActive]}><Text style={[styles.categoryChipText, draft.categoryId === String(category.id) && styles.categoryChipTextActive]}>{category.name}</Text></TouchableOpacity>)}</ScrollView> : null}<View style={styles.row}><View style={styles.half}><TextInput value={draft.rows} onChangeText={(value) => setDraft((d) => ({ ...d, rows: value.replace(/\D/g, "") }))} keyboardType="number-pad" style={styles.input} textAlign="right" placeholder="عدد الصفوف" /></View><View style={styles.half}><TextInput value={draft.columns} onChangeText={(value) => setDraft((d) => ({ ...d, columns: value.replace(/\D/g, "") }))} keyboardType="number-pad" style={styles.input} textAlign="right" placeholder="الأعمدة" /></View></View><View style={styles.toggleRow}><Text style={styles.toggleText}>تمرير أفقي للمنتجات</Text><Switch value={draft.scroll} onValueChange={(value) => setDraft((d) => ({ ...d, scroll: value }))} trackColor={{ true: "#E60023" }} /></View><View style={styles.infoBox}><MaterialIcons name="auto-awesome" size={20} color="#8B5CF6" /><Text style={styles.infoText}>يمكن وضع الفئات قبل هذه الشبكة أو بعدها، أو إخفاء بلوك الفئات ونقله بمفاتيح الترتيب أعلاه.</Text></View></> : null}
        <View style={styles.toggleRow}><Text style={styles.toggleText}>ظاهر للعملاء</Text><Switch value={draft.visible} onValueChange={(value) => setDraft((d) => ({ ...d, visible: value }))} trackColor={{ true: "#168451" }} /></View><TouchableOpacity disabled={saving} onPress={save} style={styles.saveButton}>{saving ? <ActivityIndicator color="#FFF" /> : <Text style={styles.saveText}>حفظ ونشر التصميم</Text>}</TouchableOpacity>
      </View> : null}
    </ScrollView>
  </ScreenContainer>;
}

function Preview({ section }: { section: Section }) {
  const c = section.config ?? {};
  const type = section.section_type;
  const slides = Array.isArray(c.slides) ? c.slides : [];
  const circles = Array.isArray(c.circles) ? c.circles : [];
  const products = Array.isArray(c.products) ? c.products : [];
  return <View style={styles.pSection}>
    {(type === "hero" || type === "banner") && (slides[0]?.imageUrl || c.image_url) ? <View style={styles.pHero}><Image source={{ uri: slides[0]?.imageUrl || c.image_url }} style={StyleSheet.absoluteFillObject} /><View style={styles.pShade}/><Text style={styles.pHeroTitle}>{section.title}</Text></View> : null}
    {type === "category" ? <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.pCircleRow}>{(circles.length ? circles : [{ id: "empty", title: "الفئات" }]).map((item: any) => <View key={String(item.id)} style={styles.pCircleItem}><View style={styles.pCircle}>{item.imageUrl ? <Image source={{ uri: String(item.imageUrl) }} style={StyleSheet.absoluteFillObject} /> : <MaterialIcons name="category" size={20} color="#777" />}</View><Text numberOfLines={1} style={styles.pCircleText}>{String(item.title ?? "")}</Text></View>)}</ScrollView> : null}
    {(type === "product_grid" || type === "trend") ? <><Text style={styles.pGridTitle}>{section.title}</Text><View style={styles.pGrid}>{(products.length ? products.slice(0, 6) : [{ id: 1 }, { id: 2 }, { id: 3 }, { id: 4 }]).map((item: any) => <View key={String(item.id)} style={styles.pProduct}><View style={styles.pProductImage}>{item.imageUrl ? <Image source={{ uri: item.imageUrl }} style={StyleSheet.absoluteFillObject} /> : <MaterialIcons name="image" size={18} color="#BBB" />}</View><Text numberOfLines={1} style={styles.pProductText}>{item.title ?? "منتج"}</Text></View>)}</View></> : null}
  </View>;
}

const styles = StyleSheet.create({
  header: { height: 64, backgroundColor: "#FFF", paddingHorizontal: 15, flexDirection: "row", alignItems: "center", justifyContent: "space-between", borderBottomWidth: 1, borderColor: "#EDEDED" },
  headerCopy: { flex: 1, alignItems: "flex-end", marginHorizontal: 12 }, headerTitle: { fontSize: 18, fontWeight: "900", color: "#111" }, headerSub: { fontSize: 10, color: "#888", marginTop: 2 }, headerAdd: { width: 38, height: 38, borderRadius: 19, backgroundColor: "#E60023", alignItems: "center", justifyContent: "center" },
  page: { padding: 12, paddingBottom: 220, width: "100%", maxWidth: 960, alignSelf: "center" }, center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 10 }, muted: { color: "#888", fontSize: 12 },
  quickAdd: { backgroundColor: "#FFF", borderRadius: 14, padding: 12, marginBottom: 12 }, quickTitle: { fontWeight: "900", color: "#111", textAlign: "right", marginBottom: 10 }, quickRow: { gap: 8 }, quickButton: { minWidth: 108, paddingVertical: 11, paddingHorizontal: 12, borderRadius: 12, backgroundColor: "#F7F7F8", borderWidth: 1, borderColor: "#E5E5E5", alignItems: "center", gap: 5 }, quickText: { fontSize: 10, fontWeight: "800", color: "#222" },
  previewCard: { backgroundColor: "#121212", borderRadius: 18, padding: 12, marginBottom: 14 }, previewTitle: { color: "#FFF", fontSize: 13, fontWeight: "900", textAlign: "right", marginBottom: 8 }, previewEmpty: { minHeight: 120, alignItems: "center", justifyContent: "center", gap: 8, backgroundColor: "#1B1B1B", borderRadius: 12 },
  pSection: { backgroundColor: "#FFF", borderRadius: 12, overflow: "hidden", marginBottom: 8, padding: 8 }, pHero: { height: 112, borderRadius: 10, overflow: "hidden", justifyContent: "flex-end", padding: 10, position: "relative", backgroundColor: "#EEE" }, pShade: { ...StyleSheet.absoluteFillObject, backgroundColor: "rgba(0,0,0,.22)" }, pHeroTitle: { color: "#FFF", fontSize: 16, fontWeight: "900", textAlign: "right" }, pCircleRow: { gap: 10, padding: 5 }, pCircleItem: { width: 54, alignItems: "center" }, pCircle: { width: 48, height: 48, borderRadius: 24, backgroundColor: "#F0F0F0", alignItems: "center", justifyContent: "center", overflow: "hidden" }, pCircleText: { fontSize: 8, color: "#444", marginTop: 4 }, pGridTitle: { fontSize: 12, color: "#111", fontWeight: "900", textAlign: "right", marginBottom: 6 }, pGrid: { flexDirection: "row-reverse", flexWrap: "wrap", gap: 7 }, pProduct: { width: "23%" }, pProductImage: { height: 62, backgroundColor: "#F0F0F0", borderRadius: 7, alignItems: "center", justifyContent: "center", overflow: "hidden" }, pProductText: { fontSize: 8, color: "#555", textAlign: "right", marginTop: 3 },
  sectionHeading: { fontSize: 15, fontWeight: "900", color: "#111", textAlign: "right", marginBottom: 9 }, sectionCard: { backgroundColor: "#FFF", borderRadius: 14, padding: 11, marginBottom: 8, borderWidth: 1, borderColor: "#EEE" }, selected: { borderColor: "#111" }, sectionTop: { flexDirection: "row-reverse", alignItems: "center", gap: 10 }, typeIcon: { width: 38, height: 38, borderRadius: 10, alignItems: "center", justifyContent: "center" }, sectionCopy: { flex: 1, alignItems: "flex-end" }, sectionTitle: { fontSize: 13, fontWeight: "900", color: "#222" }, sectionMeta: { fontSize: 10, color: "#888", marginTop: 3 }, sectionActions: { flexDirection: "row", alignItems: "center", gap: 5, marginTop: 9 }, iconButton: { width: 34, height: 31, borderWidth: 1, borderColor: "#E5E5E5", borderRadius: 8, alignItems: "center", justifyContent: "center" }, smallLabel: { color: "#777", fontSize: 9 },
  editorCard: { backgroundColor: "#FFF", borderRadius: 14, padding: 14, marginTop: 7 }, editorTitle: { fontSize: 16, fontWeight: "900", textAlign: "right", color: "#111", marginBottom: 12 }, input: { backgroundColor: "#F7F7F8", borderWidth: 1, borderColor: "#E3E3E5", borderRadius: 10, paddingHorizontal: 12, paddingVertical: 11, color: "#111", fontSize: 13, marginBottom: 9, flex: 1 }, multiline: { minHeight: 72, textAlignVertical: "top" }, typeRow: { gap: 7, paddingBottom: 8 }, typeButton: { paddingHorizontal: 13, paddingVertical: 9, borderRadius: 18, borderWidth: 1, borderColor: "#DDD", backgroundColor: "#FFF" }, typeButtonActive: { backgroundColor: "#111", borderColor: "#111" }, typeButtonText: { fontSize: 10, color: "#666", fontWeight: "800" }, typeButtonTextActive: { color: "#FFF" }, infoBox: { flexDirection: "row-reverse", gap: 8, backgroundColor: "#F7FBF8", borderWidth: 1, borderColor: "#DCEFE2", borderRadius: 10, padding: 11, marginBottom: 9, alignItems: "flex-start" }, infoText: { flex: 1, color: "#4E5E54", fontSize: 10, lineHeight: 17, textAlign: "right" }, mediaButton: { flexDirection: "row-reverse", alignItems: "center", justifyContent: "center", gap: 8, borderRadius: 10, borderWidth: 1, borderColor: "#F0B3BA", backgroundColor: "#FFF7F8", padding: 13, marginBottom: 9 }, mediaText: { color: "#A6001D", fontWeight: "900", fontSize: 12 }, editorImage: { width: "100%", height: 150, borderRadius: 11, backgroundColor: "#EEE", marginBottom: 9 }, fieldTitle: { fontSize: 11, fontWeight: "900", color: "#555", textAlign: "right", marginBottom: 5 }, categoryRow: { gap: 7, paddingBottom: 9 }, categoryChip: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 18, borderWidth: 1, borderColor: "#E2E2E2", backgroundColor: "#FFF" }, categoryChipActive: { backgroundColor: "#111", borderColor: "#111" }, categoryChipText: { fontSize: 10, color: "#555", fontWeight: "700" }, categoryChipTextActive: { color: "#FFF" }, row: { flexDirection: "row-reverse", gap: 9 }, half: { flex: 1 }, toggleRow: { flexDirection: "row-reverse", alignItems: "center", justifyContent: "space-between", backgroundColor: "#F8F8F8", paddingHorizontal: 10, paddingVertical: 8, borderRadius: 9, marginBottom: 9 }, toggleText: { fontSize: 12, color: "#333", fontWeight: "800" }, saveButton: { height: 48, backgroundColor: "#E60023", borderRadius: 12, alignItems: "center", justifyContent: "center", marginTop: 2 }, saveText: { color: "#FFF", fontWeight: "900", fontSize: 13 }
});
