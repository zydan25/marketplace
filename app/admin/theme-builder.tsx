import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import * as ImagePicker from "expo-image-picker";
import { router, useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Image, ScrollView, StyleSheet, Switch, Text, TextInput, TouchableOpacity, View } from "react-native";

import { AdminLayout, Colors, Font, Shadow, Spacing } from "@/components/admin";
import { StorefrontRenderer, type DynamicSection } from "@/components/storefront-renderer";
import { useCategories } from "@/hooks/use-categories";
import { useProducts } from "@/hooks/use-products";
import { djangoApi } from "@/lib/django-api";

const PRESETS = [
  { key: "fashion", title: "التصميم الجاهز الأول — الأزياء", color: "#E60023", bg: "#FFF8FA" },
  { key: "electronics", title: "التصميم الجاهز الثاني — الإلكترونيات", color: "#0D47A1", bg: "#F5F8FF" },
] as const;

type Config = Record<string, any>;
type ThemeSection = DynamicSection & { enabled?: boolean };
type ThemeRecord = { id: number; name: string; is_global: boolean; is_active: boolean; tokens: Config; layout: Config; sections: ThemeSection[] };
type Preset = { name: string; description?: string; tokens: Config; layout: Config; sections: ThemeSection[] };

const LABELS: Record<string, string> = {
  header: "الهيدر", hero: "البانر الرئيسي", banner: "البانر", promo_strip: "شريط العروض", notice: "التنبيه", category_grid: "شبكة الفئات", brand_grid: "الماركات", tabs: "التبويبات", tab: "التبويبات", catalog_toolbar: "الفرز والتصفية", product_grid: "شبكة المنتجات", trend: "الترند", bottom_nav: "التنقل السفلي",
};

export default function ThemeBuilderScreen() {
  const params = useLocalSearchParams<{ theme?: string }>();
  const requestedThemeId = Array.isArray(params.theme) ? params.theme[0] : params.theme;
  const { products } = useProducts();
  const { categories } = useCategories();
  const [themes, setThemes] = useState<ThemeRecord[]>([]);
  const [presets, setPresets] = useState<Record<string, Preset>>({});
  const [selectedId, setSelectedId] = useState<number | null>(requestedThemeId && /^\d+$/.test(requestedThemeId) ? Number(requestedThemeId) : null);
  const [draft, setDraft] = useState<ThemeRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [themeResponse, presetResponse] = await Promise.all([
        djangoApi<{ results?: ThemeRecord[] }>("/api/themes/"),
        djangoApi<Record<string, Preset>>("/api/themes/presets/"),
      ]);
      const list = themeResponse.results ?? [];
      setThemes(list);
      setPresets(presetResponse ?? {});
      setSelectedId((current) => {
        if (current && list.some((item) => item.id === current)) return current;
        return list.find((item) => item.is_global && item.is_active)?.id ?? list[0]?.id ?? null;
      });
    } catch {
      setThemes([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    const found = themes.find((theme) => theme.id === selectedId) ?? null;
    setDraft(found ? clone(found) : null);
  }, [selectedId, themes]);

  const previewSections = useMemo(() => (draft?.sections ?? []).filter((section) => section.enabled !== false), [draft]);

  const setTheme = (patch: Partial<ThemeRecord>) => setDraft((current) => current ? { ...current, ...patch } : current);
  const setTokens = (patch: Config) => setDraft((current) => current ? { ...current, tokens: { ...current.tokens, ...patch } } : current);
  const setLayout = (patch: Config) => setDraft((current) => current ? { ...current, layout: { ...current.layout, ...patch } } : current);
  const setSection = (index: number, patch: Partial<ThemeSection>) => setDraft((current) => current ? { ...current, sections: current.sections.map((item, i) => i === index ? { ...item, ...patch } : item) } : current);
  const setSectionConfig = (index: number, patch: Config) => setDraft((current) => current ? { ...current, sections: current.sections.map((item, i) => i === index ? { ...item, config: { ...(item.config ?? {}), ...patch } } : item) } : current);

  function moveSection(index: number, delta: -1 | 1) {
    setDraft((current) => {
      if (!current) return current;
      const target = index + delta;
      if (target < 0 || target >= current.sections.length) return current;
      const next = [...current.sections];
      [next[index], next[target]] = [next[target], next[index]];
      return { ...current, sections: next.map((item, i) => ({ ...item, sort_order: i + 1 })) };
    });
  }

  function addSection() {
    setDraft((current) => current ? { ...current, sections: [...current.sections, { id: `custom-${Date.now()}`, key: `custom-${Date.now()}`, type: "product_grid", title: "قسم جديد", sort_order: current.sections.length + 1, enabled: true, is_visible: true, config: { source: "latest", rows: 2, columns_mobile: 2, columns_desktop: 4, limit: 8, gap: 10 } }] } : current);
  }

  function removeSection(index: number) {
    setDraft((current) => current ? { ...current, sections: current.sections.filter((_, i) => i !== index).map((item, i) => ({ ...item, sort_order: i + 1 })) } : current);
  }

  async function addHeroImage(index: number) {
    if (!draft) return;
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], quality: 0.78, base64: true });
    if (result.canceled || !result.assets[0]?.base64) return;
    const asset = result.assets[0];
    const section = draft.sections[index];
    const slides = Array.isArray(section.config?.slides) ? [...section.config.slides] : [];
    slides.push({ id: `${section.key ?? section.id}-slide-${Date.now()}`, title: "عرض جديد", subtitle: "", ctaLabel: "استكشف الآن", url: "/collection", imageUrl: `data:${asset.mimeType ?? "image/jpeg"};base64,${asset.base64}`, visible: true, isActive: true, sortOrder: slides.length });
    setSectionConfig(index, { slides });
  }

  async function installPreset(key: string) {
    try {
      const created = await djangoApi<ThemeRecord>("/api/themes/install_preset/", { method: "POST", body: JSON.stringify({ preset: key, name: presets[key]?.name }) });
      await djangoApi(`/api/themes/${created.id}/activate/`, { method: "POST" });
      await load();
      setSelectedId(created.id);
    } catch {
      // djangoApi surfaces the server error to the normal app boundary.
    }
  }

  async function save() {
    if (!draft) return;
    setSaving(true);
    try {
      const updated = await djangoApi<ThemeRecord>(`/api/themes/${draft.id}/`, { method: "PATCH", body: JSON.stringify({ name: draft.name, tokens: draft.tokens, layout: draft.layout, sections: draft.sections }) });
      setThemes((current) => current.map((item) => item.id === updated.id ? updated : item));
      setDraft(clone(updated));
    } finally {
      setSaving(false);
    }
  }

  async function activate() {
    if (!draft) return;
    setSaving(true);
    try {
      const updated = await djangoApi<ThemeRecord>(`/api/themes/${draft.id}/activate/`, { method: "POST" });
      setThemes((current) => current.map((item) => item.is_global ? { ...item, is_active: item.id === updated.id } : item));
      setDraft((current) => current ? { ...current, is_active: true } : current);
    } finally { setSaving(false); }
  }

  async function duplicate() {
    if (!draft) return;
    setSaving(true);
    try {
      const copy = await djangoApi<ThemeRecord>(`/api/themes/${draft.id}/duplicate/`, { method: "POST", body: JSON.stringify({ name: `نسخة — ${draft.name}` }) });
      setThemes((current) => [copy, ...current]);
      setSelectedId(copy.id);
    } finally { setSaving(false); }
  }

  if (loading && !draft) return <AdminLayout title="مصمم الثيم"><View style={styles.loading}><ActivityIndicator size="large" color={Colors.primary} /><Text style={styles.loadingText}>جارٍ تحميل مكتبة التصاميم...</Text></View></AdminLayout>;

  return <AdminLayout title="مصمم الثيم المتقدم">
    <ScrollView style={{ flex: 1 }} contentContainerStyle={styles.page} showsVerticalScrollIndicator={false}>
      <View style={styles.hero}><View style={styles.heroIcon}><MaterialIcons name="dashboard-customize" size={25} color="#FFF" /></View><View style={styles.heroCopy}><Text style={styles.heroTitle}>مصمم واجهة المتجر</Text><Text style={styles.heroText}>اختر قالبًا، عدّل كل خصائصه، شاهد المعاينة نفسها التي سيستخدمها العميل، ثم احفظ أو فعّل النسخة.</Text></View><TouchableOpacity style={styles.heroButton} onPress={() => router.push("/admin/theme-library" as never)}><MaterialIcons name="style" size={16} color="#FFF" /><Text style={styles.heroButtonText}>مكتبة التصاميم</Text></TouchableOpacity></View>

      <View style={styles.card}><View style={styles.headRow}><View><Text style={styles.title}>القوالب الجاهزة</Text><Text style={styles.sub}>القالبان مبنيان كبنية مرجعية ويمكن إنشاء نسخ غير محدودة منهما.</Text></View></View><View style={styles.presetGrid}>{PRESETS.map((preset) => <View key={preset.key} style={[styles.presetCard, { backgroundColor: preset.bg, borderColor: `${preset.color}35` }]}><PreviewMini color={preset.color} /><Text style={styles.presetTitle}>{presets[preset.key]?.name ?? preset.title}</Text><Text style={styles.presetSub}>{presets[preset.key]?.description ?? ""}</Text><TouchableOpacity style={[styles.presetButton, { backgroundColor: preset.color }]} onPress={() => void installPreset(preset.key)}><Text style={styles.presetButtonText}>استخدام هذا القالب</Text></TouchableOpacity></View>)}</View></View>

      {draft ? <>
        <View style={styles.layoutColumns}>
          <View style={styles.previewColumn}><View style={styles.card}><View style={styles.headRow}><View><Text style={styles.title}>المعاينة الحية</Text><Text style={styles.sub}>تُعرض من نفس Renderer المستخدم في تطبيق العميل.</Text></View><View style={[styles.status, draft.is_active && styles.statusOn]}><Text style={styles.statusText}>{draft.is_active ? "نشط" : "مسودة"}</Text></View></View><View style={styles.previewShell}><StorefrontRenderer sections={previewSections} theme={draft as any} products={products} categories={categories.map((item) => ({ id: item.id, name: item.name, slug: item.slug, imageUrl: item.image ?? "" }))} /></View></View></View>
          <View style={styles.controlsColumn}>
            <View style={styles.card}><Text style={styles.title}>الهوية والألوان</Text><Text style={styles.sub}>كلها محفوظة داخل الثيم في الخادم.</Text><Field label="اسم التصميم" value={draft.name} onChange={(value) => setTheme({ name: value })} /><Field label="اللون الرئيسي" value={String(draft.tokens?.primary ?? "")} onChange={(value) => setTokens({ primary: value })} /><Field label="اللون الثانوي" value={String(draft.tokens?.secondary ?? "")} onChange={(value) => setTokens({ secondary: value })} /><Field label="الخلفية" value={String(draft.tokens?.background ?? "#FFF")} onChange={(value) => setTokens({ background: value })} /><Field label="السطح" value={String(draft.tokens?.surface ?? "#FFF")} onChange={(value) => setTokens({ surface: value })} /><Field label="النص" value={String(draft.tokens?.text ?? "#111")} onChange={(value) => setTokens({ text: value })} /><Field label="الحواف" value={String(draft.tokens?.border ?? "#EEE")} onChange={(value) => setTokens({ border: value })} /><NumberField label="الاستدارة" value={Number(draft.tokens?.radius ?? 12)} onChange={(value) => setTokens({ radius: value })} /></View>
            <View style={styles.card}><Text style={styles.title}>أبعاد الصفحة</Text><Field label="نوع القالب" value={String(draft.layout?.family ?? "custom")} onChange={(value) => setLayout({ family: value })} /><NumberField label="ارتفاع الهيدر" value={Number(draft.layout?.header_height ?? 64)} onChange={(value) => setLayout({ header_height: value })} /><NumberField label="ارتفاع Hero" value={Number(draft.layout?.hero_height ?? 260)} onChange={(value) => setLayout({ hero_height: value })} /><NumberField label="هامش الصفحة" value={Number(draft.layout?.page_padding ?? 12)} onChange={(value) => setLayout({ page_padding: value })} /><NumberField label="المسافة بين الأقسام" value={Number(draft.layout?.section_gap ?? 10)} onChange={(value) => setLayout({ section_gap: value })} /><NumberField label="حجم الفئة الافتراضي" value={Number(draft.layout?.category_size ?? 72)} onChange={(value) => setLayout({ category_size: value })} /><NumberField label="أعمدة المنتجات للهاتف" value={Number(draft.layout?.product_columns_mobile ?? 2)} onChange={(value) => setLayout({ product_columns_mobile: value })} /><NumberField label="أعمدة المنتجات للكمبيوتر" value={Number(draft.layout?.product_columns_desktop ?? 4)} onChange={(value) => setLayout({ product_columns_desktop: value })} /><NumberField label="مسافة المنتجات" value={Number(draft.layout?.product_gap ?? 10)} onChange={(value) => setLayout({ product_gap: value })} /><SwitchRow label="إظهار التنقل السفلي" value={Boolean(draft.layout?.show_bottom_nav)} onChange={(value) => setLayout({ show_bottom_nav: value })} /></View>
          </View>
        </View>

        <View style={styles.card}><View style={styles.headRow}><View><Text style={styles.title}>أقسام القالب</Text><Text style={styles.sub}>يمكنك ترتيب الأقسام وإخفاءها وحذفها وإضافة أقسام جديدة وتعديل خصائصها.</Text></View><TouchableOpacity style={styles.addSection} onPress={addSection}><MaterialIcons name="add" size={17} color="#FFF" /><Text style={styles.addSectionText}>إضافة قسم</Text></TouchableOpacity></View>
          {draft.sections.map((section, index) => <SectionEditor key={String(section.id ?? index)} section={section} index={index} categories={categories.map((item) => ({ id: item.id, name: item.name }))} onToggle={(value) => setSection(index, { enabled: value, is_visible: value })} onMove={(direction) => moveSection(index, direction)} onDelete={() => removeSection(index)} onTitle={(value) => setSection(index, { title: value })} onConfig={(patch) => setSectionConfig(index, patch)} onAddHeroImage={() => void addHeroImage(index)} />)}
        </View>

        <View style={styles.saveBar}><TouchableOpacity disabled={saving} style={styles.saveButton} onPress={() => void save()}>{saving ? <ActivityIndicator color="#FFF" /> : <><MaterialIcons name="save" size={18} color="#FFF" /><Text style={styles.saveText}>حفظ التعديلات</Text></>}</TouchableOpacity>{!draft.is_active ? <TouchableOpacity disabled={saving} style={styles.activateButton} onPress={() => void activate()}><MaterialIcons name="check-circle" size={18} color="#FFF" /><Text style={styles.saveText}>تفعيل التصميم</Text></TouchableOpacity> : null}<TouchableOpacity disabled={saving} style={styles.duplicateButton} onPress={() => void duplicate()}><MaterialIcons name="content-copy" size={18} color="#111" /><Text style={styles.duplicateText}>نسخ تصميم</Text></TouchableOpacity></View>
      </> : <View style={styles.empty}><Text style={styles.title}>لا يوجد تصميم محدد</Text></View>}
    </ScrollView>
  </AdminLayout>;
}

function SectionEditor({ section, index, categories, onToggle, onMove, onDelete, onTitle, onConfig, onAddHeroImage }: { section: ThemeSection; index: number; categories: Array<{ id: number; name: string }>; onToggle: (value: boolean) => void; onMove: (direction: -1 | 1) => void; onDelete: () => void; onTitle: (value: string) => void; onConfig: (patch: Config) => void; onAddHeroImage: () => void }) {
  const [open, setOpen] = useState(index < 2);
  const c = section.config ?? {};
  const type = String(section.type ?? "product_grid").toLowerCase();
  const editItems = (key: string, items: any[]) => onConfig({ [key]: items });
  const slides = Array.isArray(c.slides) ? c.slides : [];
  const items = Array.isArray(c.items) ? c.items : [];
  return <View style={[styles.sectionEditor, section.enabled === false && styles.sectionDisabled]}>
    <View style={styles.sectionHeader}><View style={styles.orderBadge}><Text style={styles.orderText}>{index + 1}</Text></View><View style={styles.sectionMain}><Text style={styles.sectionName}>{section.title || LABELS[type] || type}</Text><Text style={styles.sectionType}>{LABELS[type] || type}</Text></View><Switch value={section.enabled !== false} onValueChange={onToggle} /><TouchableOpacity style={styles.iconBtn} onPress={() => onMove(-1)}><MaterialIcons name="keyboard-arrow-up" size={20} color="#444" /></TouchableOpacity><TouchableOpacity style={styles.iconBtn} onPress={() => onMove(1)}><MaterialIcons name="keyboard-arrow-down" size={20} color="#444" /></TouchableOpacity><TouchableOpacity style={styles.iconBtn} onPress={() => setOpen((value) => !value)}><MaterialIcons name={open ? "expand-less" : "expand-more"} size={20} color="#444" /></TouchableOpacity><TouchableOpacity style={styles.deleteBtn} onPress={onDelete}><MaterialIcons name="delete-outline" size={19} color={Colors.danger} /></TouchableOpacity></View>
    {open ? <View style={styles.sectionBody}><Field label="اسم القسم" value={String(section.title ?? "")} onChange={onTitle} />
      {(type === "hero" || type === "banner") ? <><NumberField label="ارتفاع البانر" value={Number(c.height ?? 260)} onChange={(value) => onConfig({ height: value })} /><SwitchRow label="تشغيل تلقائي" value={c.autoplay !== false} onChange={(value) => onConfig({ autoplay: value })} /><NumberField label="الفاصل بين الشرائح" value={Number(c.interval_ms ?? 4500)} onChange={(value) => onConfig({ interval_ms: value })} /><TouchableOpacity style={styles.uploadButton} onPress={onAddHeroImage}><MaterialIcons name="add-photo-alternate" size={18} color="#FFF" /><Text style={styles.uploadText}>إضافة بانر</Text></TouchableOpacity>{slides.map((slide: any, i: number) => <View key={String(slide.id ?? i)} style={styles.slideEditor}><View style={styles.slidePreview}>{slide.imageUrl ? <Image source={{ uri: slide.imageUrl }} style={StyleSheet.absoluteFillObject} /> : null}</View><View style={{ flex: 1 }}><Field label={`عنوان ${i + 1}`} value={String(slide.title ?? "")} onChange={(value) => { const next=[...slides]; next[i]={...next[i],title:value}; editItems("slides", next); }} /><Field label="وصف" value={String(slide.subtitle ?? "")} onChange={(value) => { const next=[...slides]; next[i]={...next[i],subtitle:value}; editItems("slides", next); }} /><Field label="رابط" value={String(slide.url ?? "")} onChange={(value) => { const next=[...slides]; next[i]={...next[i],url:value}; editItems("slides", next); }} /></View></View>)}</> : null}
      {(type === "category_grid" || type === "category") ? <><NumberField label="عدد الصفوف" value={Number(c.rows ?? 3)} onChange={(value) => onConfig({ rows: Math.max(1,value) })} /><NumberField label="عدد الأعمدة" value={Number(c.columns ?? 4)} onChange={(value) => onConfig({ columns: Math.max(1,value) })} /><NumberField label="حجم الصورة" value={Number(c.size ?? 72)} onChange={(value) => onConfig({ size: Math.max(42,value) })} /><NumberField label="المسافة" value={Number(c.gap ?? 10)} onChange={(value) => onConfig({ gap: Math.max(4,value) })} /><NumberField label="عدد أسطر الاسم" value={Number(c.label_lines ?? 1)} onChange={(value) => onConfig({ label_lines: Math.max(1,value) })} /><CategorySelector categories={categories} selected={c.category_ids ?? []} onChange={(value) => onConfig({ category_ids: value })} /></> : null}
      {(type === "brand_grid") ? <><NumberField label="الصفوف" value={Number(c.rows ?? 1)} onChange={(value) => onConfig({ rows: Math.max(1,value) })} /><NumberField label="الأعمدة" value={Number(c.columns ?? 4)} onChange={(value) => onConfig({ columns: Math.max(1,value) })} /><NumberField label="الحجم" value={Number(c.size ?? 82)} onChange={(value) => onConfig({ size: Math.max(48,value) })} /><NumberField label="العدد" value={Number(c.limit ?? 8)} onChange={(value) => onConfig({ limit: Math.max(1,value) })} /><NumberField label="المسافة" value={Number(c.gap ?? 12)} onChange={(value) => onConfig({ gap: Math.max(4,value) })} /></> : null}
      {(type === "product_grid" || type === "trend") ? <><Field label="مصدر المنتجات" value={String(c.source ?? "latest")} onChange={(value) => onConfig({ source: value })} /><NumberField label="الصفوف" value={Number(c.rows ?? 4)} onChange={(value) => onConfig({ rows: Math.max(1,value) })} /><NumberField label="أعمدة الهاتف" value={Number(c.columns_mobile ?? 2)} onChange={(value) => onConfig({ columns_mobile: Math.max(1,value) })} /><NumberField label="أعمدة الكمبيوتر" value={Number(c.columns_desktop ?? 4)} onChange={(value) => onConfig({ columns_desktop: Math.max(1,value) })} /><NumberField label="عدد المنتجات" value={Number(c.limit ?? 8)} onChange={(value) => onConfig({ limit: Math.max(1,value) })} /><NumberField label="المسافة" value={Number(c.gap ?? 10)} onChange={(value) => onConfig({ gap: Math.max(4,value) })} /></> : null}
      {(type === "promo_strip" || type === "tabs" || type === "tab" || type === "bottom_nav") ? <VisualList items={items} onChange={(next) => onConfig({ items: next, tabs: type === "tabs" || type === "tab" ? next : c.tabs })} /> : null}
      {type === "notice" ? <Field label="نص التنبيه" value={String(c.text ?? "")} onChange={(value) => onConfig({ text: value })} multiline /> : null}
      {type === "catalog_toolbar" ? <><SwitchRow label="إظهار العدد" value={c.show_count !== false} onChange={(value) => onConfig({ show_count: value })} /><SwitchRow label="إظهار الترتيب" value={c.show_sort !== false} onChange={(value) => onConfig({ show_sort: value })} /><SwitchRow label="إظهار التصفية" value={c.show_filter !== false} onChange={(value) => onConfig({ show_filter: value })} /></> : null}
      {type === "header" ? <><SwitchRow label="الإشعارات" value={c.show_notifications !== false} onChange={(value) => onConfig({ show_notifications: value })} /><SwitchRow label="البحث" value={c.show_search !== false} onChange={(value) => onConfig({ show_search: value })} /><SwitchRow label="التبويبات العلوية" value={c.show_category_chips !== false || c.show_category_nav !== false} onChange={(value) => onConfig({ show_category_chips: value, show_category_nav: value })} /><NumberField label="عدد التصنيفات العلوية" value={Number(c.category_chip_limit ?? c.category_nav_limit ?? 6)} onChange={(value) => onConfig({ category_chip_limit: value, category_nav_limit: value })} /></> : null}
    </View> : null}
  </View>;
}

function CategorySelector({ categories, selected, onChange }: { categories: Array<{ id: number; name: string }>; selected: any[]; onChange: (ids: number[]) => void }) { const active = new Set(selected.map(String)); return <View style={{ marginTop: 8 }}><Text style={styles.blockLabel}>الفئات المحددة — عند تركها فارغة تُستخدم الفئات كلها</Text><View style={styles.categorySelector}>{categories.map((category) => { const checked = active.has(String(category.id)); return <TouchableOpacity key={category.id} style={[styles.catChip, checked && styles.catChipActive]} onPress={() => onChange(checked ? selected.filter((id) => String(id) !== String(category.id)) : [...selected, category.id])}><Text style={checked ? styles.catChipTextActive : styles.catChipText}>{category.name}</Text></TouchableOpacity>; })}</View></View>; }
function VisualList({ items, onChange }: { items: any[]; onChange: (items: any[]) => void }) { return <View style={{ marginTop: 8 }}>{items.map((item, index) => <View key={String(item.id ?? index)} style={styles.visualRow}><View style={{ flex: 1 }}><Field label="العنوان" value={String(item.title ?? item.label ?? "")} onChange={(value) => { const next=[...items]; next[index]={...next[index],title:value,label:value}; onChange(next); }} /><Field label="الرابط" value={String(item.url ?? "")} onChange={(value) => { const next=[...items]; next[index]={...next[index],url:value}; onChange(next); }} /><Field label="النص الإضافي" value={String(item.note ?? item.subtitle ?? "")} onChange={(value) => { const next=[...items]; next[index]={...next[index],note:value,subtitle:value}; onChange(next); }} /></View><TouchableOpacity style={styles.deleteBtn} onPress={() => onChange(items.filter((_, i) => i !== index))}><MaterialIcons name="delete-outline" size={19} color={Colors.danger} /></TouchableOpacity></View>)}<TouchableOpacity style={styles.addSmall} onPress={() => onChange([...items, { id: `item-${Date.now()}`, title: "عنصر جديد", label: "عنصر جديد", url: "", note: "", icon: "circle" }])}><MaterialIcons name="add" size={16} color={Colors.primary} /><Text style={styles.addSmallText}>إضافة عنصر</Text></TouchableOpacity></View>; }
function PreviewMini({ color }: { color: string }) { return <View style={{ backgroundColor: "#FFF", borderRadius: 12, padding: 7 }}><View style={{ height: 17, borderRadius: 7, backgroundColor: "#F3F4F6" }} /><View style={{ height: 58, marginTop: 5, borderRadius: 8, backgroundColor: color }} /><View style={{ flexDirection: "row-reverse", gap: 4, marginTop: 5 }}>{[1,2,3,4].map((x) => <View key={x} style={{ flex: 1, height: 16, borderRadius: 8, borderWidth: 1, borderColor: `${color}35` }} />)}</View><View style={{ flexDirection: "row-reverse", flexWrap: "wrap", gap: 4, marginTop: 5 }}>{[1,2,3,4,5,6].map((x) => <View key={x} style={{ width: "31%", height: 28, borderRadius: 6, backgroundColor: "#F7F7F7" }} />)}</View></View>; }
function Field({ label, value, onChange, multiline = false }: { label: string; value: string; onChange: (value: string) => void; multiline?: boolean }) { return <View style={styles.field}><Text style={styles.fieldLabel}>{label}</Text><TextInput value={value} onChangeText={onChange} multiline={multiline} style={[styles.input, multiline && { minHeight: 70, textAlignVertical: "top" }]} textAlign="right" /></View>; }
function NumberField({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) { return <Field label={label} value={String(value)} onChange={(raw) => { const number = Number(raw); if (Number.isFinite(number)) onChange(number); }} />; }
function SwitchRow({ label, value, onChange }: { label: string; value: boolean; onChange: (value: boolean) => void }) { return <View style={styles.switchRow}><Text style={styles.fieldLabel}>{label}</Text><Switch value={value} onValueChange={onChange} trackColor={{ false: "#D1D5DB", true: Colors.primary }} /></View>; }
function clone<T>(value: T): T { return JSON.parse(JSON.stringify(value)) as T; }

const styles = StyleSheet.create({
  page:{padding:Spacing.md,paddingBottom:120},hero:{backgroundColor:"#111827",borderRadius:22,padding:18,flexDirection:"row-reverse",alignItems:"center",gap:12,marginBottom:14,...Shadow.md},heroIcon:{width:50,height:50,borderRadius:16,backgroundColor:Colors.primary,alignItems:"center",justifyContent:"center"},heroCopy:{flex:1,alignItems:"flex-end"},heroTitle:{color:"#FFF",fontSize:20,fontWeight:"900",textAlign:"right"},heroText:{color:"#D0D7E2",fontSize:10,lineHeight:18,textAlign:"right",marginTop:4},heroButton:{height:38,paddingHorizontal:11,borderRadius:10,backgroundColor:Colors.primary,flexDirection:"row-reverse",alignItems:"center",justifyContent:"center",gap:5},heroButtonText:{color:"#FFF",fontSize:9,fontWeight:"900"},card:{backgroundColor:Colors.surface,borderWidth:1,borderColor:Colors.divider,borderRadius:18,padding:14,marginBottom:12,...Shadow.sm},headRow:{flexDirection:"row-reverse",alignItems:"center",justifyContent:"space-between",gap:10,marginBottom:11},title:{color:Colors.text,...Font.sectionTitle,textAlign:"right"},sub:{color:Colors.textSecondary,...Font.small,textAlign:"right",marginTop:3},presetGrid:{flexDirection:"row-reverse",flexWrap:"wrap",gap:12},presetCard:{flexGrow:1,flexBasis:330,minWidth:290,borderWidth:1,borderRadius:18,padding:11},presetTitle:{fontSize:13,fontWeight:"900",color:Colors.text,textAlign:"right",marginTop:9},presetSub:{fontSize:9,lineHeight:16,color:Colors.textSecondary,textAlign:"right",marginTop:3,minHeight:30},presetButton:{height:40,borderRadius:11,alignItems:"center",justifyContent:"center",marginTop:8},presetButtonText:{color:"#FFF",fontSize:10,fontWeight:"900"},layoutColumns:{flexDirection:"row-reverse",gap:12,alignItems:"flex-start"},previewColumn:{flex:1,minWidth:0},controlsColumn:{width:360,maxWidth:"100%"},previewShell:{borderRadius:12,overflow:"hidden",minHeight:500},status:{backgroundColor:"#F3F4F6",paddingHorizontal:9,paddingVertical:5,borderRadius:99},statusOn:{backgroundColor:Colors.successLight},statusText:{color:Colors.textSecondary,fontSize:8,fontWeight:"900"},field:{marginTop:8},fieldLabel:{color:Colors.text,fontSize:9,fontWeight:"900",textAlign:"right",marginBottom:5},input:{minHeight:38,borderWidth:1,borderColor:Colors.divider,backgroundColor:Colors.surfaceAlt,borderRadius:10,paddingHorizontal:10,fontSize:10,color:Colors.text},switchRow:{minHeight:42,flexDirection:"row-reverse",alignItems:"center",justifyContent:"space-between",borderBottomWidth:1,borderBottomColor:Colors.divider,marginTop:5},addSection:{height:37,borderRadius:10,paddingHorizontal:11,backgroundColor:Colors.primary,flexDirection:"row-reverse",alignItems:"center",justifyContent:"center",gap:5},addSectionText:{color:"#FFF",fontSize:9,fontWeight:"900"},sectionEditor:{borderWidth:1,borderColor:Colors.divider,borderRadius:14,marginTop:9,overflow:"hidden",backgroundColor:"#FFF"},sectionDisabled:{opacity:.55},sectionHeader:{minHeight:58,flexDirection:"row-reverse",alignItems:"center",gap:7,paddingHorizontal:10,backgroundColor:"#FAFAFA"},orderBadge:{width:28,height:28,borderRadius:14,backgroundColor:Colors.primary,alignItems:"center",justifyContent:"center"},orderText:{color:"#FFF",fontSize:9,fontWeight:"900"},sectionMain:{flex:1,alignItems:"flex-end"},sectionName:{color:Colors.text,fontSize:11,fontWeight:"900",textAlign:"right"},sectionType:{color:Colors.textSecondary,fontSize:8,marginTop:2},iconBtn:{width:31,height:31,borderRadius:8,backgroundColor:"#FFF",alignItems:"center",justifyContent:"center",borderWidth:1,borderColor:Colors.divider},deleteBtn:{width:31,height:31,borderRadius:8,backgroundColor:"#FEF2F2",alignItems:"center",justifyContent:"center"},sectionBody:{padding:11,borderTopWidth:1,borderTopColor:Colors.divider},uploadButton:{height:40,borderRadius:10,backgroundColor:Colors.primary,flexDirection:"row-reverse",alignItems:"center",justifyContent:"center",gap:6,marginTop:9},uploadText:{color:"#FFF",fontSize:9,fontWeight:"900"},slideEditor:{flexDirection:"row-reverse",gap:9,marginTop:9,padding:8,borderRadius:10,backgroundColor:"#F8FAFC"},slidePreview:{width:110,height:70,borderRadius:9,backgroundColor:"#E5E7EB",overflow:"hidden"},blockLabel:{fontSize:9,fontWeight:"900",color:Colors.text,textAlign:"right",marginTop:9,marginBottom:5},categorySelector:{flexDirection:"row-reverse",flexWrap:"wrap",gap:5},catChip:{borderWidth:1,borderColor:Colors.divider,borderRadius:99,paddingHorizontal:9,paddingVertical:6,backgroundColor:"#FFF"},catChipActive:{backgroundColor:Colors.primary,borderColor:Colors.primary},catChipText:{fontSize:8,color:Colors.textSecondary},catChipTextActive:{fontSize:8,color:"#FFF",fontWeight:"900"},visualRow:{flexDirection:"row-reverse",gap:7,borderTopWidth:1,borderTopColor:Colors.divider,paddingTop:8,marginTop:8},addSmall:{height:35,borderRadius:9,backgroundColor:Colors.surfaceAlt,flexDirection:"row-reverse",alignItems:"center",justifyContent:"center",gap:5,marginTop:8},addSmallText:{color:Colors.primary,fontSize:9,fontWeight:"900"},saveBar:{flexDirection:"row-reverse",flexWrap:"wrap",gap:8,marginBottom:20},saveButton:{minHeight:44,borderRadius:11,paddingHorizontal:15,backgroundColor:Colors.primary,flexDirection:"row-reverse",alignItems:"center",justifyContent:"center",gap:6},activateButton:{minHeight:44,borderRadius:11,paddingHorizontal:15,backgroundColor:"#16A34A",flexDirection:"row-reverse",alignItems:"center",justifyContent:"center",gap:6},duplicateButton:{minHeight:44,borderRadius:11,paddingHorizontal:15,backgroundColor:"#F3F4F6",flexDirection:"row-reverse",alignItems:"center",justifyContent:"center",gap:6},saveText:{color:"#FFF",fontSize:10,fontWeight:"900"},duplicateText:{color:"#111",fontSize:10,fontWeight:"900"},loading:{flex:1,alignItems:"center",justifyContent:"center",gap:10},loadingText:{fontSize:12,color:Colors.textSecondary},empty:{padding:40,alignItems:"center"}
});
