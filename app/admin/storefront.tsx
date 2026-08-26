import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import * as ImagePicker from "expo-image-picker";
import { Alert, FlatList, Image, ScrollView, StyleSheet, Switch, Text, TextInput, TouchableOpacity, View } from "react-native";

import { useCallback, useEffect, useMemo, useState } from "react";

import { AdminLayout, Colors, Font, Radius, Shadow, Spacing, showToast } from "@/components/admin";
import { useAuth } from "@/hooks/use-auth";
import { createCircle, createSlide, createTab, deleteCircle, deleteSlide, deleteTab, getAdminStorefront, type StorefrontCircle, type StorefrontSlide, type StorefrontTab, updateCircle, updateSlide, updateTab, updatePromos } from "@/lib/storefront-api";

type UploadedImage = { dataUrl: string; fileName: string };

async function pickOneImage(): Promise<UploadedImage | undefined> {
  const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], quality: 0.78, base64: true });
  if (result.canceled || !result.assets[0]?.base64) return undefined;
  const asset = result.assets[0];
  return { dataUrl: `data:${asset.mimeType ?? "image/jpeg"};base64,${asset.base64}`, fileName: asset.fileName ?? `storefront-${Date.now()}.jpg` };
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </View>
  );
}

function ImageSelector({ image, onPick, label }: { image?: UploadedImage; onPick: () => void; label: string }) {
  return (
    <TouchableOpacity style={styles.imagePicker} onPress={onPick}>
      {image ? (
        <Image source={{ uri: image.dataUrl }} style={styles.selectedImage} />
      ) : (
        <View style={styles.imagePickerPlaceholder}>
          <MaterialIcons name="add-photo-alternate" size={22} color={Colors.textMuted} />
          <Text style={styles.imagePickerText}>{label}</Text>
        </View>
      )}
    </TouchableOpacity>
  );
}

function VisualList({ type, items, onMove, onToggle, onDelete }: {
  type: "slide" | "circle";
  items: (StorefrontSlide | StorefrontCircle)[];
  onMove: (id: string, direction: -1 | 1) => void;
  onToggle: (id: string, isActive: boolean) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <View style={styles.visualList}>
      {items.map((item, index) => (
        <View key={item.id} style={styles.visualRow}>
          {item.imageUrl ? (
            <Image source={{ uri: item.imageUrl }} style={[styles.visualImage, type === "circle" && styles.visualCircle]} />
          ) : (
            <View style={[styles.visualImage, styles.visualBlank, type === "circle" && styles.visualCircle]}>
              <MaterialIcons name="image" size={16} color={Colors.textMuted} />
            </View>
          )}
          <View style={styles.visualCopy}>
            <Text style={styles.visualTitle}>{type === "slide" ? (item as StorefrontSlide).title || "عرض بدون عنوان" : item.title}</Text>
            <Text style={styles.visualMeta}>الترتيب {index + 1}</Text>
          </View>
          <View style={styles.visualActions}>
            <Switch value={item.isActive} onValueChange={(isActive) => onToggle(item.id, isActive)} trackColor={{ true: Colors.primary }} />
            <TouchableOpacity onPress={() => onMove(item.id, -1)} hitSlop={6}>
              <MaterialIcons name="keyboard-arrow-up" size={20} color={Colors.textSecondary} />
            </TouchableOpacity>
            <TouchableOpacity onPress={() => onMove(item.id, 1)} hitSlop={6}>
              <MaterialIcons name="keyboard-arrow-down" size={20} color={Colors.textSecondary} />
            </TouchableOpacity>
            <TouchableOpacity onPress={() => onDelete(item.id)} hitSlop={6}>
              <MaterialIcons name="delete-outline" size={20} color={Colors.danger} />
            </TouchableOpacity>
          </View>
        </View>
      ))}
    </View>
  );
}

export default function StorefrontControlScreen() {
  useAuth();
  const [tabs, setTabs] = useState<StorefrontTab[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tabTitle, setTabTitle] = useState("");
  const [placeholder, setPlaceholder] = useState("");
  const [slideTitle, setSlideTitle] = useState("");
  const [slideSubtitle, setSlideSubtitle] = useState("");
  const [slideImage, setSlideImage] = useState<UploadedImage>();
  const [circleTitle, setCircleTitle] = useState("");
  const [circleTarget, setCircleTarget] = useState("");
  const [circleImage, setCircleImage] = useState<UploadedImage>();
  const [flashTitle, setFlashTitle] = useState("");
  const [flashSubtitle, setFlashSubtitle] = useState("");
  const [freeShippingTitle, setFreeShippingTitle] = useState("");
  const [freeShippingSubtitle, setFreeShippingSubtitle] = useState("");
  const [freeShippingCategory, setFreeShippingCategory] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const next = await getAdminStorefront();
      setTabs(next);
      setSelectedId((current) => current && next.some((tab) => tab.id === current) ? current : next[0]?.id ?? null);
    } catch (error) {
      Alert.alert("تعذر تحميل إعدادات المتجر", error instanceof Error ? error.message : "حاولي مجددًا.");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const selected = useMemo(() => tabs.find((tab) => tab.id === selectedId) ?? null, [selectedId, tabs]);

  const saveTab = async () => {
    if (!tabTitle.trim()) { Alert.alert("بيانات ناقصة", "أدخلي اسم التبويب."); return; }
    try {
      setSaving(true);
      const result = await createTab({ title: tabTitle.trim(), searchPlaceholder: placeholder.trim() });
      setTabs(result.tabs); setSelectedId(result.tabs.at(-1)?.id ?? null); setTabTitle(""); setPlaceholder("");
    } catch (error) { Alert.alert("تعذر إضافة التبويب", error instanceof Error ? error.message : "حاولي مجددًا."); } finally { setSaving(false); }
  };

  const reorderTabs = async (id: string, direction: -1 | 1) => {
    const index = tabs.findIndex((tab) => tab.id === id);
    const nextIndex = index + direction;
    if (index < 0 || nextIndex < 0 || nextIndex >= tabs.length) return;
    const reordered = [...tabs]; [reordered[index], reordered[nextIndex]] = [reordered[nextIndex], reordered[index]];
    for (const [position, tab] of reordered.entries()) await updateTab(tab.id, { sortOrder: position });
    await load();
  };

  const addSlide = async () => {
    if (!selected || !slideImage) { Alert.alert("صورة العرض مطلوبة", "اختاري صورة العرض أولًا."); return; }
    try {
      setSaving(true);
      const result = await createSlide(selected.id, { title: slideTitle.trim(), subtitle: slideSubtitle.trim(), ctaLabel: "تسوّقي الآن", image: slideImage });
      setTabs(result.tabs); setSlideTitle(""); setSlideSubtitle(""); setSlideImage(undefined);
    } catch (error) { Alert.alert("تعذر إضافة العرض", error instanceof Error ? error.message : "حاولي مجددًا."); } finally { setSaving(false); }
  };

  const addCircle = async () => {
    if (!selected || !circleTitle.trim()) { Alert.alert("بيانات ناقصة", "أدخلي اسم القسم الدائري."); return; }
    try {
      setSaving(true);
      const result = await createCircle(selected.id, { title: circleTitle.trim(), targetCategory: circleTarget.trim(), ...(circleImage ? { image: circleImage } : {}) });
      setTabs(result.tabs); setCircleTitle(""); setCircleTarget(""); setCircleImage(undefined);
    } catch (error) { Alert.alert("تعذر إضافة القسم", error instanceof Error ? error.message : "حاولي مجددًا."); } finally { setSaving(false); }
  };

  const savePromos = async () => {
    if (!selected) return;
    try {
      setSaving(true);
      const result = await updatePromos(selected.id, {
        flashTitle: flashTitle.trim() || "تخفيضات سريعة", flashSubtitle: flashSubtitle.trim() || "عرض المزيد", flashMode: "flash",
        freeShippingTitle: freeShippingTitle.trim() || "شحن مجاني", freeShippingSubtitle: freeShippingSubtitle.trim() || "أضيفي المزيد للحصول عليه", freeShippingCategory: freeShippingCategory.trim(),
      });
      setTabs(result.tabs);
      showToast("تم الحفظ بنجاح", "success");
    } catch (error) { Alert.alert("تعذر حفظ العروض", error instanceof Error ? error.message : "حاولي مجددًا."); } finally { setSaving(false); }
  };

  const reorderVisual = async (items: (StorefrontSlide | StorefrontCircle)[], id: string, direction: -1 | 1, kind: "slide" | "circle") => {
    const index = items.findIndex((item) => item.id === id);
    const target = index + direction;
    if (index < 0 || target < 0 || target >= items.length) return;
    const reordered = [...items]; [reordered[index], reordered[target]] = [reordered[target], reordered[index]];
    for (const [position, item] of reordered.entries()) {
      if (kind === "slide") await updateSlide(item.id, { sortOrder: position });
      else await updateCircle(item.id, { sortOrder: position });
    }
    await load();
  };

  return (
    <AdminLayout title="التحكم بالشريط العلوي">
      <ScrollView style={{ flex: 1 }} contentContainerStyle={styles.content} showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">
        {/* Intro banner */}
        <View style={styles.intro}>
          <View style={styles.introIcon}>
            <MaterialIcons name="view-carousel" size={22} color={Colors.textInverse} />
          </View>
          <View style={styles.introCopy}>
            <Text style={styles.introTitle}>تبويبات وعروض وأقسام المتجر</Text>
            <Text style={styles.introText}>أضيفي التبويبات ثم اختاري أحدها لإدارة صور العرض والأيقونات الدائرية.</Text>
          </View>
        </View>

        <Section title="إضافة تبويب علوي">
          <TextInput value={tabTitle} onChangeText={setTabTitle} placeholder="مثال: نسائي أو داخلية" placeholderTextColor={Colors.textMuted} style={styles.input} textAlign="right" />
          <TextInput value={placeholder} onChangeText={setPlaceholder} placeholder="نص البحث لهذا التبويب (اختياري)" placeholderTextColor={Colors.textMuted} style={[styles.input, { marginTop: Spacing.sm }]} textAlign="right" />
          <TouchableOpacity disabled={saving} style={styles.primaryBtn} onPress={saveTab}>
            <Text style={styles.primaryBtnText}>إضافة إلى الشريط العلوي</Text>
          </TouchableOpacity>
        </Section>

        <Section title="تبويبات الشريط">
          <FlatList data={tabs} horizontal inverted keyExtractor={(item) => item.id} contentContainerStyle={styles.tabsList} renderItem={({ item }) => (
            <TouchableOpacity onPress={() => setSelectedId(item.id)} style={[styles.tabChip, selected?.id === item.id && styles.tabChipActive]}>
              <Text style={[styles.tabChipText, selected?.id === item.id && styles.tabChipTextActive]}>{item.title}</Text>
            </TouchableOpacity>
          )} />
          {!loading && !tabs.length ? <Text style={styles.emptyText}>لا يوجد أي تبويب بعد.</Text> : null}
          {selected && (
            <View style={styles.tabActions}>
              <TouchableOpacity onPress={() => reorderTabs(selected.id, -1)}><MaterialIcons name="keyboard-arrow-up" size={22} color={Colors.textSecondary} /></TouchableOpacity>
              <TouchableOpacity onPress={() => reorderTabs(selected.id, 1)}><MaterialIcons name="keyboard-arrow-down" size={22} color={Colors.textSecondary} /></TouchableOpacity>
              <TouchableOpacity onPress={() => Alert.alert("حذف التبويب", `هل أنتِ متأكد من حذف "${selected.title}"؟`, [{ text: "إلغاء" }, { text: "حذف", style: "destructive", onPress: async () => { await deleteTab(selected.id); await load(); } }])}>
                <MaterialIcons name="delete-outline" size={22} color={Colors.danger} />
              </TouchableOpacity>
            </View>
          )}
        </Section>

        {selected && (
          <>
            <Section title="صور العرض (Hero Slides)">
              <TextInput value={slideTitle} onChangeText={setSlideTitle} placeholder="عنوان العرض" placeholderTextColor={Colors.textMuted} style={styles.input} textAlign="right" />
              <TextInput value={slideSubtitle} onChangeText={setSlideSubtitle} placeholder="النص الفرعي (اختياري)" placeholderTextColor={Colors.textMuted} style={[styles.input, { marginTop: Spacing.sm }]} textAlign="right" />
              <View style={{ marginVertical: Spacing.md }}>
                <ImageSelector image={slideImage} onPick={async () => { const img = await pickOneImage(); if (img) setSlideImage(img); }} label="اختيار صورة العرض" />
              </View>
              <TouchableOpacity disabled={saving} style={styles.primaryBtn} onPress={addSlide}>
                <Text style={styles.primaryBtnText}>إضافة عرض</Text>
              </TouchableOpacity>
              {selected.slides.length > 0 && <VisualList type="slide" items={selected.slides} onMove={(id, dir) => reorderVisual(selected.slides, id, dir, "slide")} onToggle={async (id, isActive) => { await updateSlide(id, { isActive }); await load(); }} onDelete={(id) => Alert.alert("حذف", "هل أنتِ متأكد؟", [{ text: "إلغاء" }, { text: "حذف", style: "destructive", onPress: async () => { await deleteSlide(id); await load(); } }])} />}
            </Section>

            <Section title="الأقسام الدائرية">
              <TextInput value={circleTitle} onChangeText={setCircleTitle} placeholder="اسم القسم" placeholderTextColor={Colors.textMuted} style={styles.input} textAlign="right" />
              <TextInput value={circleTarget} onChangeText={setCircleTarget} placeholder="الفئة المستهدفة (اختياري)" placeholderTextColor={Colors.textMuted} style={[styles.input, { marginTop: Spacing.sm }]} textAlign="right" />
              <View style={{ marginVertical: Spacing.md }}>
                <ImageSelector image={circleImage} onPick={async () => { const img = await pickOneImage(); if (img) setCircleImage(img); }} label="اختيار أيونة القسم" />
              </View>
              <TouchableOpacity disabled={saving} style={styles.primaryBtn} onPress={addCircle}>
                <Text style={styles.primaryBtnText}>إضافة قسم</Text>
              </TouchableOpacity>
              {selected.circles.length > 0 && <VisualList type="circle" items={selected.circles} onMove={(id, dir) => reorderVisual(selected.circles, id, dir, "circle")} onToggle={async (id, isActive) => { await updateCircle(id, { isActive }); await load(); }} onDelete={(id) => Alert.alert("حذف", "هل أنتِ متأكد؟", [{ text: "إلغاء" }, { text: "حذف", style: "destructive", onPress: async () => { await deleteCircle(id); await load(); } }])} />}
            </Section>

            <Section title="العروض الترويجية">
              <Text style={styles.promoGroupTitle}>التخفيضات السريعة</Text>
              <TextInput value={flashTitle} onChangeText={setFlashTitle} placeholder="عنوان التخفيض" placeholderTextColor={Colors.textMuted} style={styles.input} textAlign="right" />
              <TextInput value={flashSubtitle} onChangeText={setFlashSubtitle} placeholder="النص الفرعي" placeholderTextColor={Colors.textMuted} style={[styles.input, { marginTop: Spacing.sm }]} textAlign="right" />
              <Text style={[styles.promoGroupTitle, { marginTop: Spacing.lg }]}>الشحن المجاني</Text>
              <TextInput value={freeShippingTitle} onChangeText={setFreeShippingTitle} placeholder="عنوان الشحن" placeholderTextColor={Colors.textMuted} style={styles.input} textAlign="right" />
              <TextInput value={freeShippingSubtitle} onChangeText={setFreeShippingSubtitle} placeholder="النص الفرعي" placeholderTextColor={Colors.textMuted} style={[styles.input, { marginTop: Spacing.sm }]} textAlign="right" />
              <TextInput value={freeShippingCategory} onChangeText={setFreeShippingCategory} placeholder="الفئة المستهدفة للشحن المجاني (اختياري)" placeholderTextColor={Colors.textMuted} style={[styles.input, { marginTop: Spacing.sm }]} textAlign="right" />
              <TouchableOpacity disabled={saving} style={styles.primaryBtn} onPress={savePromos}>
                <Text style={styles.primaryBtnText}>{saving ? "جارِ الحفظ..." : "حفظ إعدادات العروض"}</Text>
              </TouchableOpacity>
            </Section>
          </>
        )}
      </ScrollView>
    </AdminLayout>
  );
}

const styles = StyleSheet.create({
  content: { padding: Spacing.lg, paddingBottom: Spacing["4xl"] },

  /* Intro */
  intro: { backgroundColor: Colors.black, borderRadius: Radius.lg, padding: Spacing.xl, flexDirection: "row-reverse", gap: Spacing.md, alignItems: "flex-start", marginBottom: Spacing.lg, ...Shadow.raised },
  introIcon: { width: 44, height: 44, borderRadius: Radius.sm, backgroundColor: Colors.primary, alignItems: "center", justifyContent: "center" },
  introCopy: { flex: 1, alignItems: "flex-end" },
  introTitle: { color: Colors.textInverse, ...Font.cardTitle },
  introText: { color: "#A0A0A5", ...Font.small, textAlign: "right", marginTop: Spacing.xs, lineHeight: 18 },

  /* Section */
  section: { backgroundColor: Colors.surface, borderRadius: Radius.md, padding: Spacing.lg, marginBottom: Spacing.md, ...Shadow.soft },
  sectionTitle: { color: Colors.text, ...Font.sectionTitle, textAlign: "right", marginBottom: Spacing.md },

  input: { height: 46, backgroundColor: Colors.surfaceAlt, borderRadius: Radius.sm, borderWidth: 1, borderColor: Colors.border, paddingHorizontal: Spacing.md, color: Colors.text, fontSize: 14, writingDirection: "rtl" as const },

  primaryBtn: { height: 46, backgroundColor: Colors.primary, borderRadius: Radius.sm, alignItems: "center", justifyContent: "center", marginTop: Spacing.md, ...Shadow.raised },
  primaryBtnText: { color: Colors.textInverse, ...Font.button },

  /* Tabs */
  tabsList: { gap: Spacing.sm, paddingBottom: Spacing.sm },
  tabChip: { borderRadius: Radius.sm, borderWidth: 1, borderColor: Colors.border, paddingHorizontal: Spacing.lg, paddingVertical: Spacing.sm, backgroundColor: Colors.surface },
  tabChipActive: { backgroundColor: Colors.black, borderColor: Colors.black },
  tabChipText: { color: Colors.textSecondary, ...Font.chip },
  tabChipTextActive: { color: Colors.textInverse, fontWeight: "700" },
  tabActions: { flexDirection: "row-reverse", gap: Spacing.md, marginTop: Spacing.sm },

  /* Visual list */
  visualList: { marginTop: Spacing.md },
  visualRow: { flexDirection: "row-reverse", alignItems: "center", gap: Spacing.md, paddingVertical: Spacing.md, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: Colors.divider },
  visualImage: { width: 48, height: 48, borderRadius: Radius.sm, resizeMode: "cover" as const },
  visualCircle: { borderRadius: 24 },
  visualBlank: { backgroundColor: Colors.surfaceAlt, alignItems: "center", justifyContent: "center" },
  visualCopy: { flex: 1, alignItems: "flex-end" },
  visualTitle: { color: Colors.text, ...Font.cardTitle },
  visualMeta: { color: Colors.textMuted, ...Font.tiny, marginTop: 2 },
  visualActions: { flexDirection: "row-reverse", alignItems: "center", gap: Spacing.xs },

  /* Image picker */
  imagePicker: { height: 90, borderRadius: Radius.sm, borderWidth: 2, borderColor: Colors.border, borderStyle: "dashed" as const, overflow: "hidden" },
  imagePickerPlaceholder: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: Colors.surfaceAlt },
  imagePickerText: { color: Colors.textMuted, ...Font.tiny, marginTop: Spacing.xs },
  selectedImage: { width: "100%", height: "100%", resizeMode: "cover" as const },

  /* Promos */
  promoGroupTitle: { color: Colors.text, ...Font.label, textAlign: "right", marginBottom: Spacing.sm },

  emptyText: { color: Colors.textMuted, ...Font.small, textAlign: "right", marginTop: Spacing.sm },
});
