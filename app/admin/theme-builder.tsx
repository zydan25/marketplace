import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import * as ImagePicker from "expo-image-picker";
import { router } from "expo-router";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Image, ScrollView, StyleSheet, Switch, Text, TextInput, TouchableOpacity, View } from "react-native";

import { AdminLayout, Colors, Font, Shadow, Spacing } from "@/components/admin";
import { StorefrontRenderer, type DynamicSection } from "@/components/storefront-renderer";
import { useCategories } from "@/hooks/use-categories";
import { useProducts } from "@/hooks/use-products";
import { djangoApi } from "@/lib/django-api";
import type { StorefrontTheme } from "@/lib/storefront-api";

const PRESET_KEYS = ["fashion", "electronics"] as const;
type ThemeRecord = StorefrontTheme & { name: string; is_active: boolean };
type Config = Record<string, any>;
type Section = DynamicSection & { config: Config; enabled?: boolean };
type Preset = { name: string; description?: string; tokens: Config; layout: Config; sections: Section[] };

const SECTION_LABELS: Record<string, string> = {
  header: "الهيدر",
  hero: "البانر الرئيسي",
  promo_strip: "شريط العروض",
  notice: "شريط التنبيه",
  category_grid: "شبكة الفئات",
  brand_grid: "الماركات",
  tabs: "التبويبات",
  catalog_toolbar: "أدوات الفرز والتصفية",
  product_grid: "شبكة المنتجات",
  bottom_nav: "التنقل السفلي",
};

export default function ThemeBuilderScreen() {
  const { products } = useProducts();
  const { categories } = useCategories();
  const [themes, setThemes] = useState<ThemeRecord[]>([]);
  const [presets, setPresets] = useState<Record<string, Preset>>({});
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [draft, setDraft] = useState<ThemeRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [installing, setInstalling] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [themeResult, presetResult] = await Promise.all([
        djangoApi<{ results?: ThemeRecord[] }>("/api/themes/"),
        djangoApi<Record<string, Preset>>("/api/themes/presets/"),
      ]);
      const list = themeResult.results ?? [];
      setThemes(list);
      setPresets(presetResult ?? {});
      setSelectedId((current) => current && list.some((item) => item.id === current) ? current : list.find((item) => item.is_global && item.is_active)?.id ?? list[0]?.id ?? null);
    } catch {
      setThemes([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    const found = themes.find((item) => item.id === selectedId) ?? null;
    setDraft(found ? cloneTheme(found) : null);
  }, [selectedId, themes]);

  const previewSections = useMemo(() => (draft?.sections ?? []).filter((item) => item.enabled !== false), [draft]);

  async function installPreset(key: string) {
    const preset = presets[key];
    if (!preset) return;
    setInstalling(key);
    try {
      const created = await djangoApi<ThemeRecord>("/api/themes/install_preset/", { method: "POST", body: JSON.stringify({ preset: key }) });
      await djangoApi(`/api/themes/${created.id}/activate/`, { method: "POST" });
      await load();
      setSelectedId(created.id);
    } catch {
      // handled by normal admin network errors in djangoApi
    } finally {
      setInstalling(null);
    }
  }

  async function saveDraft() {
    if (!draft) return;
    setSaving(true);
    try {
      const updated = await djangoApi<ThemeRecord>(`/api/themes/${draft.id}/`, {
        method: "PATCH",
        body: JSON.stringify({ name: draft.name, tokens: draft.tokens, layout: draft.layout, sections: draft.sections }),
      });
      setThemes((current) => current.map((item) => item.id === updated.id ? updated : item));
      setDraft(cloneTheme(updated));
    } finally {
      setSaving(false);
    }
  }

  async function activateDraft() {
    if (!draft) return;
    setSaving(true);
    try {
      const updated = await djangoApi<ThemeRecord>(`/api/themes/${draft.id}/activate/`, { method: "POST" });
      setThemes((current) => current.map((item) => item.is_global ? { ...item, is_active: item.id === updated.id } : item));
      setDraft((current) => current ? { ...current, is_active: true } : current);
    } finally {
      setSaving(false);
    }
  }

  async function duplicateDraft() {
    if (!draft) return;
    setSaving(true);
    try {
      const copy = await djangoApi<ThemeRecord>(`/api/themes/${draft.id}/duplicate/`, { method: "POST", body: JSON.stringify({ name: `نسخة — ${draft.name}` }) });
      setThemes((current) => [copy, ...current]);
      setSelectedId(copy.id);
    } finally {
      setSaving(false);
    }
  }

  function updateDraft(patch: Partial<ThemeRecord>) { setDraft((current) => current ? { ...current, ...patch } : current); }
  function updateTokens(patch: Config) { setDraft((current) => current ? { ...current, tokens: { ...current.tokens, ...patch } } : current); }
  function updateLayout(patch: Config) { setDraft((current) => current ? { ...current, layout: { ...current.layout, ...patch } } : current); }
  function updateSection(index: number, patch: Partial<Section>) { setDraft((current) => current ? { ...current, sections: current.sections.map((item, i) => i === index ? { ...item, ...patch } : item) } : current); }
  function updateSectionConfig(index: number, patch: Config) { setDraft((current) => current ? { ...current, sections: current.sections.map((item, i) => i === index ? { ...item, config: { ...item.config, ...patch } } : item) } : current); }
  function moveSection(index: number, direction: -1 | 1) {
    setDraft((current) => {
      if (!current) return current;
      const next = [...current.sections];
      const target = index + direction;
      if (target < 0 || target >= next.length) return current;
      [next[index], next[target]] = [next[target], next[index]];
      return { ...current, sections: next.map((item, i) => ({ ...item, sort_order: i + 1 })) };
    });
  }
  function removeSection(index: number) { setDraft((current) => current ? { ...current, sections: current.sections.filter((_, i) => i !== index).map((item, i) => ({ ...item, sort_order: i + 1 })) } : current); }
  function addSection() {
    setDraft((current) => current ? { ...current, sections: [...current.sections, { key: `custom-${Date.now()}`, id: `custom-${Date.now()}`, type: "product_grid", title: "قسم جديد", sort_order: current.sections.length + 1, is_visible: true, enabled: true, config: { source: "latest", rows: 2, columns_mobile: 2, columns_desktop: 4, limit: 8, gap: 10 } } as Section] } : current);
  }

  async function addHeroImage(index: number) {
    if (!draft) return;
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], quality: 0.78, base64: true });
    if (result.canceled || !result.assets[0]?.base64) return;
    const asset = result.assets[0];
    const dataUrl = `data:${asset.mimeType ?? "image/jpeg"};base64,${asset.base64}`;
    const section = draft.sections[index];
    const slides = Array.isArray(section.config?.slides) ? [...section.config.slides] : [];
    slides.push({ id: `${section.key}-slide-${Date.now()}`, title: "عرض جديد", subtitle: "", ctaLabel: "استكشف الآن", url: "/collection", imageUrl: dataUrl, visible: true, isActive: true, sortOrder: slides.length });
    updateSectionConfig(index, { slides });
  }

  if (loading && !draft) return <AdminLayout title="مصمم الثيم"><View style={styles.loading}><ActivityIndicator size="large" color={Colors.primary} /><Text style={styles.loadingText}>جارٍ تحميل مكتبة التصاميم...</Text></View></AdminLayout>;

  return (
    <AdminLayout title="مصمم الثيم المتقدم">
      <ScrollView style={{ flex: 1 }} contentContainerStyle={styles.page} showsVerticalScrollIndicator={false}>
        <View style={styles.hero}>
          <View style={styles.heroIcon}><MaterialIcons name="dashboard-customize" size={25} color="#FFF" /></View>
          <View style={styles.heroCopy}>
            <Text style={styles.heroTitle}>مصمم واجهة المتجر</Text>
            <Text style={styles.heroText}>تحكم كامل في القالب، البانرات، الفئات، الصفوف والأعمدة، البطاقات، الألوان، المسافات، التنقل والأقسام. كل تعديل يُحفظ في الخادم ويُقرأ مباشرة من تطبيق العميل.</Text>
          </View>
          <View style={styles.heroActions}>
            <TouchableOpacity style={styles.heroButton} onPress={() => router.push("/admin/theme-library" as never)}><MaterialIcons name="style" size={16} color="#FFF" /><Text style={styles.heroButtonText}>مكتبة التصاميم</Text></TouchableOpacity>
            <TouchableOpacity style={styles.heroButtonMuted} onPress={() => router.push("/admin/storefront-sections" as never)}><MaterialIcons name="view-list" size={16} color="#FFF" /><Text style={styles.heroButtonText}>المحرر القديم</Text></TouchableOpacity>
          </View>
        </View>

        <View style={styles.card}>
          <View style={styles.headRow}><View><Text style={styles.title}>القوالب الجاهزة المرجعية</Text><Text style={styles.sub}>القالبان مبنيان على بنية الصورتين المرجعيتين، ويمكن إنشاء نسخ مستقلة منهما.</Text></View></View>
          <View style={styles.presetRow}>
            {PRESET_KEYS.map((key) => {
              const preset = presets[key];
              const active = draft?.is_active && draft.layout?.family === key;
              return <View key={key} style={[styles.presetCard, { borderColor: key === "electronics" ? "#0D47A135" : "#E6002335" }]}>
                <PreviewMini family={key} primary={String(preset?.tokens?.primary ?? (key === "electronics" ? "#0D47A1" : "#E60023"))} />
                <Text style={styles.presetTitle}>{preset?.name ?? key}</Text>
                <Text style={styles.presetSub}>{preset?.description ?? ""}</Text>
                <TouchableOpacity disabled={!preset || !!installing} onPress={() => installPreset(key)} style={[styles.presetButton, { backgroundColor: key === "electronics" ? "#0D47A1" : "#E60023" }]}>{installing === key ? <ActivityIndicator color="#FFF" /> : <Text style={styles.presetButtonText}>{active ? "مفعّل — إعادة إنشاء نسخة" : "استخدام هذا القالب"}</Text>}</TouchableOpacity>
              </View>;
            })}
          </View>
        </View>

        {draft ? <>
          <View style={styles.layoutColumns}>
            <View style={styles.leftColumn}>
              <View style={styles.card}>
                <View style={styles.headRow}><View><Text style={styles.title}>المعاينة الحية</Text><Text style={styles.sub}>هذه هي نفس بنية الـRenderer التي سيستخدمها تطبيق العميل.</Text></View><View style={[styles.activeChip, draft.is_active && styles.activeChipOn]}><Text style={styles.activeChipText}>{draft.is_active ? "نشط" : "غير نشط"}</Text></View></View>
                <View style={[styles.previewShell, { backgroundColor: String(draft.tokens?.background ?? "#FFF") }]}>
                  <StorefrontRenderer sections={previewSections} theme={draft} products={products} categories={categories.map((item) => ({ id: item.id, name: item.name, slug: item.slug, imageUrl: item.image ?? "" }))} />
                </View>
              </View>
            </View>

            <View style={styles.rightColumn}>
              <View style={styles.card}>
                <Text style={styles.title}>هوية التصميم</Text>
                <Text style={styles.sub}>الألوان العامة ونوع القالب.</Text>
                <Field label="اسم التصميم" value={draft.name} onChange={(value) => updateDraft({ name: value })} />
                <Field label="اللون الرئيسي" value={String(draft.tokens?.primary ?? "")} onChange={(value) => updateTokens({ primary: value })} />
                <Field label="اللون الثانوي" value={String(draft.tokens?.secondary ?? "")} onChange={(value) => updateTokens({ secondary: value })} />
                <Field label="لون الخلفية" value={String(draft.tokens?.background ?? "")} onChange={(value) => updateTokens({ background: value })} />
                <Field label="لون السطح" value={String(draft.tokens?.surface ?? "")} onChange={(value) => updateTokens({ surface: value })} />
                <Field label="النص" value={String(draft.tokens?.text ?? "")} onChange={(value) => updateTokens({ text: value })} />
                <Field label="الحواف" value={String(draft.tokens?.border ?? "#EEEEEE")} onChange={(value) => updateTokens({ border: value })} />
                <NumberField label="استدارة البطاقات" value={draft.tokens?.radius ?? 12} onChange={(value) => updateTokens({ radius: value })} />
              </View>

              <View style={styles.card}>
                <Text style={styles.title}>إعدادات الصفحة</Text>
                <Text style={styles.sub}>تحكم في الأبعاد العامة للقالب.</Text>
                <Field label="عائلة القالب" value={String(draft.layout?.family ?? "custom")} onChange={(value) => updateLayout({ family: value })} />
                <Field label="نمط الهيدر" value={String(draft.layout?.header ?? "")} onChange={(value) => updateLayout({ header: value })} />
                <NumberField label="ارتفاع الهيدر" value={draft.layout?.header_height ?? 64} onChange={(value) => updateLayout({ header_height: value })} />
                <NumberField label="ارتفاع الـHero" value={draft.layout?.hero_height ?? 260} onChange={(value) => updateLayout({ hero_height: value })} />
                <NumberField label="هامش الصفحة" value={draft.layout?.page_padding ?? 12} onChange={(value) => updateLayout({ page_padding: value })} />
                <NumberField label="المسافة بين الأقسام" value={draft.layout?.section_gap ?? 10} onChange={(value) => updateLayout({ section_gap: value })} />
                <NumberField label="حجم الفئة الافتراضي" value={draft.layout?.category_size ?? 72} onChange={(value) => updateLayout({ category_size: value })} />
                <NumberField label="عدد أعمدة المنتجات للهاتف" value={draft.layout?.product_columns_mobile ?? 2} onChange={(value) => updateLayout({ product_columns_mobile: value })} />
                <NumberField label="عدد أعمدة المنتجات للكمبيوتر" value={draft.layout?.product_columns_desktop ?? 4} onChange={(value) => updateLayout({ product_columns_desktop: value })} />
                <NumberField label="ارتفاع صورة المنتج" value={draft.layout?.product_image_height ?? 190} onChange={(value) => updateLayout({ product_image_height: value })} />
                <SwitchRow label="إظهار شريط التنقل السفلي" value={Boolean(draft.layout?.show_bottom_nav)} onChange={(value) => updateLayout({ show_bottom_nav: value })} />
              </View>
            </View>
          </View>

          <View style={styles.card}>
            <View style={styles.headRow}><View><Text style={styles.title}>أقسام التصميم</Text><Text style={styles.sub}>فعّل، أخفِ، رتّب، احذف أو أضف أي قسم، ثم اضبط خصائصه بالتفصيل.</Text></View><TouchableOpacity style={styles.addSectionButton} onPress={addSection}><MaterialIcons name="add" size={17} color="#FFF" /><Text style={styles.addSectionText}>إضافة قسم</Text></TouchableOpacity></View>
            {draft.sections.map((section, index) => <SectionEditor key={String(section.id ?? index)} section={section} index={index} categories={categories} onToggle={(value) => updateSection(index, { enabled: value })} onMove={(dir) => moveSection(index, dir)} onDelete={() => removeSection(index)} onTitle={(value) => updateSection(index, { title: value })} onConfig={(patch) => updateSectionConfig(index, patch)} onHeroImage={() => addHeroImage(index)} />)}
          </View>

          <View style={styles.saveBar}>
            <TouchableOpacity disabled={saving} style={styles.saveButton} onPress={saveDraft}>{saving ? <ActivityIndicator color="#FFF" /> : <><MaterialIcons name="save" size={18} color="#FFF" /><Text style={styles.saveText}>حفظ كل التعديلات</Text></>}</TouchableOpacity>
            {!draft.is_active ? <TouchableOpacity disabled={saving} style={styles.activateButton} onPress={activateDraft}><MaterialIcons name="check-circle" size={18} color="#FFF" /><Text style={styles.saveText}>تفعيل هذا التصميم</Text></TouchableOpacity> : null}
            <TouchableOpacity disabled={saving} style={styles.duplicateButton} onPress={duplicateDraft}><MaterialIcons name="content-copy" size={18} color="#111" /><Text style={styles.duplicateText}>نسخ تصميم جديد</Text></TouchableOpacity>
          </View>
        </> : null}
      </ScrollView>
    </AdminLayout>
  );
}

function SectionEditor({ section, index, categories, onToggle, onMove, onDelete, onTitle, onConfig, onHeroImage }: { section: Section; index: number; categories: Array<{ id: number; name: string; slug: string }>; onToggle: (value: boolean) => void; onMove: (dir: -1 | 1) => void; onDelete: () => void; onTitle: (value: string) => void; onConfig: (patch: Config) => void; onHeroImage: () => void }) {
  const [open, setOpen] = useState(index < 2);
  const c = section.config ?? {};
  const type = String(section.type ?? "product_grid");
  const setItems = (key: string, items: any[]) => onConfig({ [key]: items });

  return <View style={[styles.sectionEditor, !section.enabled && styles.sectionDisabled]}>
    <View style={styles.sectionHeader}>
      <View style={styles.orderCircle}><Text style={styles.orderText}>{index + 1}</Text></View>
      <View style={styles.sectionMain}><Text style={styles.sectionName}>{section.title || SECTION_LABELS[type] || type}</Text><Text style={styles.sectionType}>{SECTION_LABELS[type] || type}</Text></View>
      <Switch value={section.enabled !== false} onValueChange={onToggle} />
      <TouchableOpacity onPress={() => onMove(-1)} style={styles.iconButton}><MaterialIcons name="keyboard-arrow-up" size={20} color="#444" /></TouchableOpacity>
      <TouchableOpacity onPress={() => onMove(1)} style={styles.iconButton}><MaterialIcons name="keyboard-arrow-down" size={20} color="#444" /></TouchableOpacity>
      <TouchableOpacity onPress={() => setOpen((value) => !value)} style={styles.expandButton}><MaterialIcons name={open ? "expand-less" : "expand-more"} size={21} color="#111" /></TouchableOpacity>
      <TouchableOpacity onPress={onDelete} style={styles.deleteIcon}><MaterialIcons name="delete-outline" size={19} color={Colors.danger} /></TouchableOpacity>
    </View>
    {open ? <View style={styles.sectionBody}>
      <Field label="اسم القسم" value={String(section.title ?? "")} onChange={onTitle} />
      {type === "hero" || type === "banner" ? <>
        <NumberField label="ارتفاع البانر" value={c.height ?? 260} onChange={(value) => onConfig({ height: value })} />
        <SwitchRow label="تشغيل تلقائي" value={c.autoplay !== false} onChange={(value) => onConfig({ autoplay: value })} />
        <NumberField label="الفاصل بين الشرائح بالمللي ثانية" value={c.interval_ms ?? 4500} onChange={(value) => onConfig({ interval_ms: value })} />
        <TouchableOpacity style={styles.uploadButton} onPress={onHeroImage}><MaterialIcons name="add-photo-alternate" size={18} color="#FFF" /><Text style={styles.uploadText}>إضافة بانر من الجهاز</Text></TouchableOpacity>
        <Text style={styles.helper}>يمكنك إضافة عدة بانرات، ثم تعديل الرابط والعنوان من بيانات الشريحة.</Text>
        {(c.slides ?? []).map((slide: any, slideIndex: number) => <View key={String(slide.id ?? slideIndex)} style={styles.slideEditor}><View style={styles.slidePreview}>{slide.imageUrl ? <Image source={{ uri: slide.imageUrl }} style={StyleSheet.absoluteFillObject} resizeMode="cover" /> : <MaterialIcons name="image" size={28} color="#AAA" />}</View><View style={{ flex: 1 }}><Field label={`عنوان البانر ${slideIndex + 1}`} value={String(slide.title ?? "")} onChange={(value) => { const next = [...(c.slides ?? [])]; next[slideIndex] = { ...next[slideIndex], title: value }; setItems("slides", next); }} /><Field label="رابط البانر" value={String(slide.url ?? "")} onChange={(value) => { const next = [...(c.slides ?? [])]; next[slideIndex] = { ...next[slideIndex], url: value }; setItems("slides", next); }} /></View></View>)}
      </> : null}
      {type === "category_grid" || type === "category" ? <>
        <NumberField label="عدد الصفوف" value={c.rows ?? 3} onChange={(value) => onConfig({ rows: Math.max(1, value) })} />
        <NumberField label="عدد الأعمدة" value={c.columns ?? 4} onChange={(value) => onConfig({ columns: Math.max(1, value) })} />
        <NumberField label="حجم الدائرة / الصورة" value={c.size ?? 72} onChange={(value) => onConfig({ size: value })} />
        <NumberField label="المسافة بين العناصر" value={c.gap ?? 10} onChange={(value) => onConfig({ gap: value })} />
        <NumberField label="عدد أسطر الاسم" value={c.label_lines ?? 1} onChange={(value) => onConfig({ label_lines: value })} />
        <CategorySelector categories={categories} selected={c.category_ids ?? []} onChange={(ids) => onConfig({ category_ids: ids })} />
      </> : null}
      {type === "brand_grid" ? <>
        <NumberField label="عدد الصفوف" value={c.rows ?? 1} onChange={(value) => onConfig({ rows: value })} />
        <NumberField label="عدد الأعمدة" value={c.columns ?? 4} onChange={(value) => onConfig({ columns: value })} />
        <NumberField label="حجم الماركة" value={c.size ?? 82} onChange={(value) => onConfig({ size: value })} />
        <NumberField label="عدد الماركات" value={c.limit ?? 8} onChange={(value) => onConfig({ limit: value })} />
        <NumberField label="المسافة" value={c.gap ?? 12} onChange={(value) => onConfig({ gap: value })} />
      </> : null}
      {type === "product_grid" || type === "trend" ? <>
        <Field label="مصدر المنتجات" value={String(c.source ?? "latest")} onChange={(value) => onConfig({ source: value })} />
        <NumberField label="عدد الصفوف" value={c.rows ?? 4} onChange={(value) => onConfig({ rows: value })} />
        <NumberField label="أعمدة الهاتف" value={c.columns_mobile ?? 2} onChange={(value) => onConfig({ columns_mobile: value })} />
        <NumberField label="أعمدة الكمبيوتر" value={c.columns_desktop ?? 4} onChange={(value) => onConfig({ columns_desktop: value })} />
        <NumberField label="عدد المنتجات" value={c.limit ?? 8} onChange={(value) => onConfig({ limit: value })} />
        <NumberField label="المسافة بين المنتجات" value={c.gap ?? 10} onChange={(value) => onConfig({ gap: value })} />
        <Field label="نمط البطاقة" value={String(c.card_style ?? "rounded")} onChange={(value) => onConfig({ card_style: value })} />
        <SwitchRow label="إظهار زر عرض الكل" value={c.show_see_all !== false} onChange={(value) => onConfig({ show_see_all: value })} />
      </> : null}
      {type === "promo_strip" ? <VisualList label="بطاقات العرض" items={c.items ?? []} empty={[] } onChange={(items) => onConfig({ items })} fields={["title", "value", "note"]} /> : null}
      {type === "notice" ? <Field label="نص التنبيه" value={String(c.text ?? "")} onChange={(value) => onConfig({ text: value })} multiline /> : null}
      {type === "tabs" || type === "tab" ? <VisualList label="عناصر التبويب" items={c.items ?? c.tabs ?? []} onChange={(items) => onConfig({ items, tabs: items })} fields={["title", "url"]} /> : null}
      {type === "catalog_toolbar" ? <><SwitchRow label="إظهار العدد" value={c.show_count !== false} onChange={(value) => onConfig({ show_count: value })} /><SwitchRow label="إظهار الترتيب" value={c.show_sort !== false} onChange={(value) => onConfig({ show_sort: value })} /><SwitchRow label="إظهار التصفية" value={c.show_filter !== false} onChange={(value) => onConfig({ show_filter: value })} /></> : null}
      {type === "bottom_nav" ? <VisualList label="عناصر التنقل" items={c.items ?? []} onChange={(items) => onConfig({ items })} fields={["label", "icon", "url"]} /> : null}
    </View> : null}
  </View>;
}

function VisualList({ label, items, onChange, fields }: { label: string; items: any[]; empty?: any[]; onChange: (items: any[]) => void; fields: string[] }) {
  return <View style={{ marginTop: 8 }}><Text style={styles.blockLabel}>{label}</Text>{items.map((item, index) => <View key={String(item.id ?? index)} style={styles.visualRow}><View style={{ flex: 1 }}>{fields.map((field) => <Field key={field} label={field} value={String(item[field] ?? "")} onChange={(value) => { const next = [...items]; next[index] = { ...next[index], [field]: value }; onChange(next); }} />)}</View><TouchableOpacity onPress={() => onChange(items.filter((_, i) => i !== index))} style={styles.deleteSmall}><MaterialIcons name="delete-outline" size={18} color={Colors.danger} /></TouchableOpacity></View>)}<TouchableOpacity style={styles.addSmall} onPress={() => onChange([...items, { id: `item-${Date.now()}`, title: "عنصر جديد", label: "عنصر جديد", value: "", note: "", url: "", icon: "circle" }])}><MaterialIcons name="add" size={16} color={Colors.primary} /><Text style={styles.addSmallText}>إضافة عنصر</Text></TouchableOpacity></View>;
}

function CategorySelector({ categories, selected, onChange }: { categories: Array<{ id: number; name: string }>; selected: any[]; onChange: (ids: number[]) => void }) {
  const selectedSet = new Set(selected.map(String));
  return <View style={{ marginTop: 8 }}><Text style={styles.blockLabel}>الفئات المحددة — اتركها كلها لاستخدام جميع الفئات</Text><View style={styles.categorySelector}>{categories.map((category) => { const checked = selectedSet.has(String(category.id)); return <TouchableOpacity key={category.id} style={[styles.catChip, checked && styles.catChipActive]} onPress={() => onChange(checked ? selected.filter((id) => String(id) !== String(category.id)) : [...selected, category.id])}><Text style={checked ? styles.catChipTextActive : styles.catChipText}>{category.name}</Text></TouchableOpacity>; })}</View></View>;
}

function PreviewMini({ family, primary }: { family: string; primary: string }) { return <View style={[styles.miniPreview, { backgroundColor: family === "electronics" ? "#F4F8FF" : "#FFF8FA" }]}><View style={styles.miniSearch} /><View style={[styles.miniHero, { backgroundColor: primary }]}><View style={styles.miniLineLg} /><View style={styles.miniLineSm} /><View style={styles.miniPhoto} /></View><View style={styles.miniPills}>{[1, 2, 3, 4].map((item) => <View key={item} style={[styles.miniPill, { borderColor: `${primary}40` }]} />)}</View><View style={styles.miniGrid}>{[1, 2, 3, 4, 5, 6].map((item) => <View key={item} style={styles.miniCard} />)}</View></View>; }
function Field({ label, value, onChange, multiline = false }: { label: string; value: string; onChange: (value: string) => void; multiline?: boolean }) { return <View style={styles.field}><Text style={styles.fieldLabel}>{label}</Text><TextInput value={value} onChangeText={onChange} multiline={multiline} style={[styles.input, multiline && { minHeight: 72, textAlignVertical: "top" }]} textAlign="right" /></View>; }
function NumberField({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) { return <Field label={label} value={String(value)} onChange={(raw) => { const parsed = Number(raw); if (Number.isFinite(parsed)) onChange(parsed); }} />; }
function SwitchRow({ label, value, onChange }: { label: string; value: boolean; onChange: (value: boolean) => void }) { return <View style={styles.switchRow}><Text style={styles.fieldLabel}>{label}</Text><Switch value={value} onValueChange={onChange} trackColor={{ false: "#D1D5DB", true: Colors.primary }} /></View>; }
function cloneTheme(theme: ThemeRecord): ThemeRecord { return JSON.parse(JSON.stringify(theme)) as ThemeRecord; }

const styles = StyleSheet.create({
  page: { padding: Spacing.md, paddingBottom: 120 },
  hero: { backgroundColor: "#111827", borderRadius: 22, padding: 18, flexDirection: "row-reverse", alignItems: "center", gap: 12, marginBottom: 14, ...Shadow.md },
  heroIcon: { width: 50, height: 50, borderRadius: 16, backgroundColor: Colors.primary, alignItems: "center", justifyContent: "center" },
  heroCopy: { flex: 1, alignItems: "flex-end" },
  heroTitle: { color: "#FFF", fontSize: 20, fontWeight: "900", textAlign: "right" },
  heroText: { color: "#D0D7E2", fontSize: 10, lineHeight: 18, textAlign: "right", marginTop: 4 },
  heroActions: { gap: 6 },
  heroButton: { height: 38, paddingHorizontal: 11, borderRadius: 10, backgroundColor: Colors.primary, flexDirection: "row-reverse", alignItems: "center", justifyContent: "center", gap: 5 },
  heroButtonMuted: { height: 38, paddingHorizontal: 11, borderRadius: 10, backgroundColor: "#263244", flexDirection: "row-reverse", alignItems: "center", justifyContent: "center", gap: 5 },
  heroButtonText: { color: "#FFF", fontSize: 9, fontWeight: "900" },
  card: { backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.divider, borderRadius: 18, padding: 14, marginBottom: 12, ...Shadow.sm },
  headRow: { flexDirection: "row-reverse", alignItems: "center", justifyContent: "space-between", gap: 10, marginBottom: 11 },
  title: { color: Colors.text, ...Font.sectionTitle, textAlign: "right" },
  sub: { color: Colors.textSecondary, ...Font.small, textAlign: "right", marginTop: 3 },
  presetRow: { flexDirection: "row-reverse", flexWrap: "wrap", gap: 12 },
  presetCard: { flexGrow: 1, flexBasis: 340, minWidth: 290, borderWidth: 1, borderRadius: 18, padding: 11, backgroundColor: "#FFF" },
  miniPreview: { borderRadius: 12, padding: 8, minHeight: 180 },
  miniSearch: { height: 20, borderRadius: 10, backgroundColor: "#FFF", borderWidth: 1, borderColor: "#E5E7EB" },
  miniHero: { height: 76, marginTop: 6, borderRadius: 9, padding: 7, flexDirection: "row-reverse", alignItems: "center", justifyContent: "space-between" },
  miniLineLg: { width: "42%", height: 8, borderRadius: 5, backgroundColor: "#FFF" },
  miniLineSm: { position: "absolute", right: 8, bottom: 8, width: "26%", height: 5, borderRadius: 4, backgroundColor: "#FFFFFF99" },
  miniPhoto: { width: "45%", height: "84%", borderRadius: 8, backgroundColor: "#FFFFFF3A" },
  miniPills: { flexDirection: "row-reverse", gap: 5, marginTop: 7 },
  miniPill: { width: 42, height: 16, borderRadius: 9, backgroundColor: "#FFF", borderWidth: 1 },
  miniGrid: { flexDirection: "row-reverse", flexWrap: "wrap", gap: 5, marginTop: 7 },
  miniCard: { width: "31%", height: 32, borderRadius: 7, backgroundColor: "#FFF", borderWidth: 1, borderColor: "#E5E7EB" },
  presetTitle: { fontSize: 13, fontWeight: "900", color: Colors.text, textAlign: "right", marginTop: 9 },
  presetSub: { fontSize: 9, lineHeight: 16, color: Colors.textSecondary, textAlign: "right", marginTop: 3, minHeight: 32 },
  presetButton: { height: 40, borderRadius: 11, alignItems: "center", justifyContent: "center", marginTop: 8 },
  presetButtonText: { color: "#FFF", fontSize: 10, fontWeight: "900" },
  layoutColumns: { flexDirection: "row-reverse", gap: 12, alignItems: "flex-start" },
  leftColumn: { flex: 1, minWidth: 0 },
  rightColumn: { width: 360, maxWidth: "100%" },
  previewShell: { borderRadius: 12, overflow: "hidden", minHeight: 500 },
  activeChip: { backgroundColor: "#F3F4F6", paddingHorizontal: 10, paddingVertical: 5, borderRadius: 99 },
  activeChipOn: { backgroundColor: Colors.successLight },
  activeChipText: { color: Colors.textSecondary, fontSize: 8, fontWeight: "900" },
  field: { marginTop: 8 },
  fieldLabel: { color: Colors.text, fontSize: 9, fontWeight: "900", textAlign: "right", marginBottom: 5 },
  input: { minHeight: 38, borderWidth: 1, borderColor: Colors.divider, backgroundColor: Colors.surfaceAlt, borderRadius: 10, paddingHorizontal: 10, fontSize: 10, color: Colors.text },
  switchRow: { minHeight: 42, flexDirection: "row-reverse", alignItems: "center", justifyContent: "space-between", borderBottomWidth: 1, borderBottomColor: Colors.divider, marginTop: 5 },
  sectionEditor: { borderWidth: 1, borderColor: Colors.divider, borderRadius: 14, marginTop: 9, overflow: "hidden", backgroundColor: "#FFF" },
  sectionDisabled: { opacity: 0.6 },
  sectionHeader: { minHeight: 58, flexDirection: "row-reverse", alignItems: "center", gap: 7, paddingHorizontal: 10, backgroundColor: "#FAFAFA" },
  orderCircle: { width: 28, height: 28, borderRadius: 14, backgroundColor: Colors.primary, alignItems: "center", justifyContent: "center" },
  orderText: { color: "#FFF", fontSize: 9, fontWeight: "900" },
  sectionMain: { flex: 1, alignItems: "flex-end" },
  sectionName: { color: Colors.text, fontSize: 11, fontWeight: "900", textAlign: "right" },
  sectionType: { color: Colors.textSecondary, fontSize: 8, marginTop: 2 },
  iconButton: { width: 31, height: 31, borderRadius: 8, backgroundColor: "#FFF", alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: Colors.divider },
  expandButton: { width: 33, height: 31, borderRadius: 8, backgroundColor: "#FFF", alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: Colors.divider },
  deleteIcon: { width: 31, height: 31, borderRadius: 8, backgroundColor: "#FEF2F2", alignItems: "center", justifyContent: "center" },
  sectionBody: { padding: 11, borderTopWidth: 1, borderTopColor: Colors.divider },
  uploadButton: { height: 40, borderRadius: 10, backgroundColor: Colors.primary, flexDirection: "row-reverse", alignItems: "center", justifyContent: "center", gap: 6, marginTop: 9 },
  uploadText: { color: "#FFF", fontSize: 9, fontWeight: "900" },
  helper: { color: Colors.textSecondary, fontSize: 8, lineHeight: 15, textAlign: "right", marginTop: 5 },
  slideEditor: { flexDirection: "row-reverse", gap: 9, marginTop: 9, padding: 8, borderRadius: 10, backgroundColor: "#F8FAFC" },
  slidePreview: { width: 110, height: 70, borderRadius: 9, backgroundColor: "#E5E7EB", overflow: "hidden", alignItems: "center", justifyContent: "center" },
  blockLabel: { fontSize: 9, fontWeight: "900", color: Colors.text, textAlign: "right", marginTop: 9, marginBottom: 5 },
  categorySelector: { flexDirection: "row-reverse", flexWrap: "wrap", gap: 5 },
  catChip: { borderWidth: 1, borderColor: Colors.divider, borderRadius: 99, paddingHorizontal: 9, paddingVertical: 6, backgroundColor: "#FFF" },
  catChipActive: { backgroundColor: Colors.primary, borderColor: Colors.primary },
  catChipText: { fontSize: 8, color: Colors.textSecondary },
  catChipTextActive: { fontSize: 8, color: "#FFF", fontWeight: "900" },
  visualRow: { flexDirection: "row-reverse", gap: 7, borderTopWidth: 1, borderTopColor: Colors.divider, paddingTop: 8, marginTop: 8 },
  deleteSmall: { width: 32, height: 32, borderRadius: 8, backgroundColor: "#FEF2F2", alignItems: "center", justifyContent: "center", marginTop: 5 },
  addSmall: { height: 35, borderRadius: 9, backgroundColor: Colors.surfaceAlt, flexDirection: "row-reverse", alignItems: "center", justifyContent: "center", gap: 5, marginTop: 8 },
  addSmallText: { color: Colors.primary, fontSize: 9, fontWeight: "900" },
  addSectionButton: { height: 37, borderRadius: 10, paddingHorizontal: 11, backgroundColor: Colors.primary, flexDirection: "row-reverse", alignItems: "center", justifyContent: "center", gap: 5 },
  addSectionText: { color: "#FFF", fontSize: 9, fontWeight: "900" },
  saveBar: { flexDirection: "row-reverse", flexWrap: "wrap", gap: 8, marginTop: 3, marginBottom: 20 },
  saveButton: { minHeight: 44, borderRadius: 11, paddingHorizontal: 15, backgroundColor: Colors.primary, flexDirection: "row-reverse", alignItems: "center", justifyContent: "center", gap: 6 },
  activateButton: { minHeight: 44, borderRadius: 11, paddingHorizontal: 15, backgroundColor: "#16A34A", flexDirection: "row-reverse", alignItems: "center", justifyContent: "center", gap: 6 },
  duplicateButton: { minHeight: 44, borderRadius: 11, paddingHorizontal: 15, backgroundColor: "#F3F4F6", flexDirection: "row-reverse", alignItems: "center", justifyContent: "center", gap: 6 },
  saveText: { color: "#FFF", fontSize: 10, fontWeight: "900" },
  duplicateText: { color: "#111", fontSize: 10, fontWeight: "900" },
  loading: { flex: 1, alignItems: "center", justifyContent: "center", gap: 10 },
  loadingText: { fontSize: 12, color: Colors.textSecondary },
});
