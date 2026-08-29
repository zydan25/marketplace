import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import * as ImagePicker from "expo-image-picker";
import { useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Alert, Image, Pressable, ScrollView, StyleSheet, Switch, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import { ScreenContainer } from "@/components/screen-container";
import { djangoApi } from "@/lib/django-api";

type Item = Record<string, any>;
type SectionType = "hero" | "banner" | "category" | "product_grid" | "trend";
type Section = { id: number; title: string; section_type: SectionType; config: Item; sort_order: number; is_visible: boolean };
type Category = { id: number; name: string; slug: string; image?: string | null };

const TYPES: Array<{ id: SectionType; label: string; hint: string; icon: string }> = [
  { id: "hero", label: "واجهة رئيسية", hint: "صورة كبيرة", icon: "view-carousel" },
  { id: "banner", label: "بانرات", hint: "عروض وصور", icon: "image" },
  { id: "category", label: "الفئات", hint: "تصنيفات المتجر", icon: "category" },
  { id: "product_grid", label: "المنتجات", hint: "شبكة المنتجات", icon: "grid-view" },
  { id: "trend", label: "الترند", hint: "الأكثر رواجًا", icon: "local-fire-department" },
];

export default function VendorStorefrontScreen() {
  const [sections, setSections] = useState<Section[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [draft, setDraft] = useState<Item>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  async function load() {
    try {
      setLoading(true);
      const [sectionData, categoryData] = await Promise.all([
        djangoApi<{ results?: Section[] }>("/api/storefront-sections/"),
        djangoApi<{ results?: Category[] }>("/api/categories/"),
      ]);
      setSections((sectionData.results ?? []).sort((a, b) => a.sort_order - b.sort_order));
      setCategories(categoryData.results ?? []);
    } catch (error) {
      Alert.alert("تعذر تحميل المصمم", error instanceof Error ? error.message : "حدث خطأ أثناء تحميل واجهة المتجر.");
    } finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  const current = useMemo(() => selected == null ? null : sections.find((section) => section.id === selected) ?? null, [selected, sections]);
  const slides = Array.isArray(draft.slides) ? draft.slides : [];
  const circles = Array.isArray(draft.category_circles) ? draft.category_circles : [];

  function openSection(section: Section) {
    setSelected(section.id);
    setDraft({ ...(section.config ?? {}), title: section.title, section_type: section.section_type, is_visible: section.is_visible });
  }

  async function createSection(type: SectionType) {
    const config = type === "category"
      ? { published: true, mode: "automatic", category_circles: [] }
      : type === "product_grid" || type === "trend"
        ? { published: true, source: type === "trend" ? "trending" : "latest", rows: 2, columns: 2, scroll: true, show_categories: true }
        : { published: true, slides: [] };
    try {
      const created = await djangoApi<Section>("/api/storefront-sections/", {
        method: "POST",
        body: JSON.stringify({ title: TYPES.find((item) => item.id === type)?.label ?? "قسم جديد", section_type: type, config, sort_order: sections.length, is_visible: true }),
      });
      setSections((old) => [...old, created].sort((a, b) => a.sort_order - b.sort_order));
      openSection(created);
    } catch (error) {
      Alert.alert("تعذر إضافة القسم", error instanceof Error ? error.message : "تحقق من اعتماد المتجر وصلاحيات الحساب.");
    }
  }

  function removeSection(id: number) {
    Alert.alert("حذف القسم", "سيُحذف القسم من واجهة المتجر فقط، ولن تُحذف المنتجات أو الصور الأصلية.", [
      { text: "إلغاء", style: "cancel" },
      { text: "حذف", style: "destructive", onPress: async () => {
        try {
          await djangoApi(`/api/storefront-sections/${id}/`, { method: "DELETE" });
          setSections((old) => old.filter((item) => item.id !== id));
          if (selected === id) { setSelected(null); setDraft({}); }
        } catch (error) { Alert.alert("تعذر الحذف", error instanceof Error ? error.message : "لا يمكن حذف القسم الآن."); }
      } },
    ]);
  }

  async function chooseImage() {
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], allowsEditing: false, quality: 0.82, base64: true });
    const asset = result.assets?.[0];
    return !result.canceled && asset?.base64 ? `data:${asset.mimeType ?? "image/jpeg"};base64,${asset.base64}` : "";
  }

  async function addBanner() {
    const imageUrl = selected == null ? "" : await chooseImage();
    if (!imageUrl) return;
    setDraft((old) => ({ ...old, slides: [...(Array.isArray(old.slides) ? old.slides : []), { id: `${selected}-${Date.now()}`, title: "عرض جديد", subtitle: "", ctaLabel: "تسوّق الآن", url: "", imageUrl, visible: true, sortOrder: slides.length }] }));
  }

  async function addCategoryCircle() {
    if (!categories.length) return Alert.alert("لا توجد فئات", "أضف الفئات من إدارة الكتالوج أولًا.");
    Alert.alert("اختر الفئة", "بعد اختيارها اختر صورة مناسبة للفئة.", categories.slice(0, 12).map((category) => ({
      text: category.name,
      onPress: async () => {
        const imageUrl = await chooseImage();
        if (!imageUrl) return;
        setDraft((old) => ({ ...old, category_circles: [...(Array.isArray(old.category_circles) ? old.category_circles : []), { id: `custom-${Date.now()}`, category_id: category.id, title: category.name, targetCategory: category.slug, url: `/collection?category=${encodeURIComponent(category.slug)}`, imageUrl, visible: true, isActive: true, sortOrder: circles.length }] }));
      },
    })));
  }

  async function saveSection() {
    if (selected == null || !current) return;
    setSaving(true);
    try {
      const payload = {
        title: String(draft.title ?? current.title),
        section_type: current.section_type,
        is_visible: Boolean(draft.is_visible),
        config: Object.fromEntries(Object.entries(draft).filter(([key]) => !["title", "section_type", "is_visible"].includes(key))),
      };
      const updated = await djangoApi<Section>(`/api/storefront-sections/${selected}/`, { method: "PATCH", body: JSON.stringify(payload) });
      setSections((old) => old.map((item) => item.id === updated.id ? updated : item));
      Alert.alert("تم الحفظ", "تم نشر التغييرات على واجهة متجرك.");
    } catch (error) { Alert.alert("تعذر الحفظ", error instanceof Error ? error.message : "تحقق من البيانات والصور."); }
    finally { setSaving(false); }
  }

  async function moveSection(id: number, direction: -1 | 1) {
    const ordered = [...sections].sort((a, b) => a.sort_order - b.sort_order);
    const from = ordered.findIndex((item) => item.id === id), to = from + direction;
    if (from < 0 || to < 0 || to >= ordered.length) return;
    [ordered[from], ordered[to]] = [ordered[to], ordered[from]];
    try {
      for (let index = 0; index < ordered.length; index++) await djangoApi(`/api/storefront-sections/${ordered[index].id}/`, { method: "PATCH", body: JSON.stringify({ sort_order: index }) });
      setSections(ordered.map((item, index) => ({ ...item, sort_order: index })));
    } catch (error) { Alert.alert("تعذر الترتيب", error instanceof Error ? error.message : "تعذر حفظ ترتيب الأقسام."); }
  }

  if (loading) return <ScreenContainer><View style={s.center}><ActivityIndicator size="large" color="#E11D48"/><Text style={s.loading}>نجهّز مساحة التصميم...</Text></View></ScreenContainer>;

  return <ScreenContainer className="bg-[#F3F4F6]" edges={["top", "bottom", "left", "right"]}>
    <View style={s.header}><TouchableOpacity style={s.headerButton} onPress={() => router.back()}><MaterialIcons name="arrow-forward" size={23} color="#111"/></TouchableOpacity><View style={s.headerCopy}><Text style={s.headerTitle}>مصمم واجهة المتجر</Text><Text style={s.headerSub}>رتّب واجهتك وأنشئ تجربة مميزة لعملائك</Text></View><TouchableOpacity style={s.headerButton} onPress={() => router.push("/vendor/design" as never)}><MaterialIcons name="palette" size={21} color="#111"/></TouchableOpacity></View>
    <ScrollView contentContainerStyle={s.page}>
      <View style={s.banner}><View style={s.bannerIcon}><MaterialIcons name="auto-awesome" size={23} color="#FFF"/></View><View style={s.bannerCopy}><Text style={s.bannerTitle}>كل جزء من متجرك في مكان واحد</Text><Text style={s.bannerText}>أضف صورة رئيسية، بانرات، فئات، منتجات وترندات، ثم رتبها واحفظها متى شئت.</Text></View></View>
      <View style={s.headRow}><Text style={s.headTitle}>أقسام جاهزة</Text><Text style={s.headMeta}>{sections.length} أقسام</Text></View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={s.typeRow}>{TYPES.map((type) => <Pressable key={type.id} onPress={() => createSection(type.id)} style={({pressed}) => [s.typeCard, pressed && { opacity: 0.72 }]}><View style={s.typeIcon}><MaterialIcons name={type.icon as any} size={21} color="#E11D48"/></View><Text style={s.typeTitle}>{type.label}</Text><Text style={s.typeHint}>{type.hint}</Text></Pressable>)}</ScrollView>
      <View style={s.headRow}><Text style={s.headTitle}>ترتيب واجهة المتجر</Text><Text style={s.headMeta}>الأسهم للحركة</Text></View>
      {sections.length === 0 ? <View style={s.empty}><MaterialIcons name="dashboard-customize" size={45} color="#C2C3C7"/><Text style={s.emptyTitle}>ابدأ من هنا</Text><Text style={s.emptyText}>اختر أحد أنواع الأقسام لإضافة أول جزء إلى الصفحة.</Text></View> : sections.map((section, index) => { const type = TYPES.find((item) => item.id === section.section_type); return <View key={section.id} style={[s.card, selected === section.id && s.selected]}><View style={s.cardMain}><View style={[s.iconBox, selected === section.id && s.iconBoxActive]}><MaterialIcons name={(type?.icon ?? "view-module") as any} size={19} color={selected === section.id ? "#FFF" : "#E11D48"}/></View><View style={s.cardCopy}><Text style={s.cardTitle}>{section.title || type?.label}</Text><Text style={s.cardMeta}>{type?.label ?? section.section_type} · القسم {index + 1}</Text></View><Switch value={section.is_visible} onValueChange={(value) => { setSections((old) => old.map((item) => item.id === section.id ? { ...item, is_visible: value } : item)); djangoApi(`/api/storefront-sections/${section.id}/`, { method: "PATCH", body: JSON.stringify({ is_visible: value }) }).catch(load); }}/></View><View style={s.actionRow}><TouchableOpacity style={s.editPill} onPress={() => openSection(section)}><MaterialIcons name="edit" size={15} color="#111"/><Text style={s.editText}>تحرير</Text></TouchableOpacity><TouchableOpacity style={s.arrow} disabled={index === 0} onPress={() => moveSection(section.id, -1)}><MaterialIcons name="keyboard-arrow-up" size={19} color={index === 0 ? "#CCC" : "#111"}/></TouchableOpacity><TouchableOpacity style={s.arrow} disabled={index === sections.length - 1} onPress={() => moveSection(section.id, 1)}><MaterialIcons name="keyboard-arrow-down" size={19} color={index === sections.length - 1 ? "#CCC" : "#111"}/></TouchableOpacity><TouchableOpacity style={s.deletePill} onPress={() => removeSection(section.id)}><MaterialIcons name="delete-outline" size={15} color="#B42318"/><Text style={s.deleteText}>حذف</Text></TouchableOpacity></View></View>; })}
      {current ? <View style={s.editor}><View style={s.editorHead}><View style={s.liveBadge}><View style={s.dot}/><Text style={s.liveText}>جاهز للنشر</Text></View><View><Text style={s.editorTitle}>تحرير القسم</Text><Text style={s.editorSub}>{current.title || "قسم الواجهة"}</Text></View></View><Text style={s.label}>عنوان القسم</Text><TextInput value={String(draft.title ?? "")} onChangeText={(value) => setDraft((old) => ({ ...old, title: value }))} placeholder="مثال: عروض هذا الأسبوع" style={s.input} textAlign="right"/><View style={s.visibility}><View><Text style={s.visibilityTitle}>إظهار للعملاء</Text><Text style={s.visibilityHint}>يمكنك إخفاء القسم دون حذفه.</Text></View><Switch value={Boolean(draft.is_visible)} onValueChange={(value) => setDraft((old) => ({ ...old, is_visible: value }))}/></View>{current.section_type === "category" ? <><TouchableOpacity style={s.mediaButton} onPress={addCategoryCircle}><MaterialIcons name="add-photo-alternate" size={20} color="#E11D48"/><Text style={s.mediaText}>إضافة فئة وصورة</Text></TouchableOpacity>{circles.map((circle: Item, index: number) => <View style={s.mediaItem} key={String(circle.id ?? index)}>{circle.imageUrl ? <Image source={{ uri: String(circle.imageUrl) }} style={s.thumb}/> : <View style={s.thumbPlaceholder}><MaterialIcons name="category" size={19} color="#AAA"/></View>}<View style={s.mediaCopy}><Text style={s.mediaTitle}>{String(circle.title ?? "فئة")}</Text><TouchableOpacity onPress={() => setDraft((old) => ({ ...old, category_circles: (old.category_circles ?? []).filter((_: Item, i: number) => i !== index) }))}><Text style={s.removeText}>حذف</Text></TouchableOpacity></View></View>)}</> : null}{current.section_type === "hero" || current.section_type === "banner" ? <><TouchableOpacity style={s.mediaButton} onPress={addBanner}><MaterialIcons name="add-photo-alternate" size={20} color="#E11D48"/><Text style={s.mediaText}>إضافة صورة أو بانر</Text></TouchableOpacity>{slides.map((slide: Item, index: number) => <View style={s.mediaItem} key={String(slide.id ?? index)}>{slide.imageUrl ? <Image source={{ uri: String(slide.imageUrl) }} style={s.bannerThumb}/> : <View style={s.bannerThumb}/>}<View style={s.mediaCopy}><TextInput value={String(slide.title ?? "")} onChangeText={(value) => setDraft((old) => ({ ...old, slides: (old.slides ?? []).map((item: Item, i: number) => i === index ? { ...item, title: value } : item) }))} style={s.smallInput} textAlign="right" placeholder="عنوان البانر"/><TouchableOpacity onPress={() => setDraft((old) => ({ ...old, slides: (old.slides ?? []).filter((_: Item, i: number) => i !== index) }))}><Text style={s.removeText}>حذف البانر</Text></TouchableOpacity></View></View>)}</> : null}{current.section_type === "product_grid" || current.section_type === "trend" ? <><Text style={s.label}>مصدر المنتجات</Text><ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={s.choiceRow}>{[["latest","الأحدث"],["trending","الترند"],["category","حسب الفئة"]].map(([value, label]) => <TouchableOpacity key={value} onPress={() => setDraft((old) => ({ ...old, source: current.section_type === "trend" ? "trending" : value }))} style={[s.choice, draft.source === value && s.choiceActive]}><Text style={draft.source === value ? s.choiceActiveText : s.choiceText}>{label}</Text></TouchableOpacity>)}</ScrollView></> : null}<TouchableOpacity disabled={saving} style={s.save} onPress={saveSection}>{saving ? <ActivityIndicator color="#FFF"/> : <><MaterialIcons name="publish" size={19} color="#FFF"/><Text style={s.saveText}>حفظ ونشر التغييرات</Text></>}</TouchableOpacity></View> : null}
    </ScrollView>
  </ScreenContainer>;
}

const s = StyleSheet.create({
  center:{flex:1,alignItems:"center",justifyContent:"center",gap:10},loading:{fontSize:12,color:"#777"},
  header:{height:70,backgroundColor:"#FFF",paddingHorizontal:14,flexDirection:"row",alignItems:"center",borderBottomWidth:1,borderColor:"#E6E6E8"},headerButton:{width:40,height:40,borderRadius:12,backgroundColor:"#F5F5F6",alignItems:"center",justifyContent:"center"},headerCopy:{flex:1,alignItems:"flex-end",marginHorizontal:11},headerTitle:{fontSize:18,fontWeight:"900",color:"#111"},headerSub:{fontSize:9,color:"#888",marginTop:3,textAlign:"right"},page:{padding:13,paddingBottom:150,maxWidth:980,width:"100%",alignSelf:"center"},banner:{backgroundColor:"#111",borderRadius:20,padding:16,flexDirection:"row-reverse",alignItems:"center",marginBottom:16},bannerIcon:{width:45,height:45,borderRadius:14,backgroundColor:"#E11D48",alignItems:"center",justifyContent:"center"},bannerCopy:{flex:1,paddingHorizontal:10,alignItems:"flex-end"},bannerTitle:{color:"#FFF",fontSize:15,fontWeight:"900"},bannerText:{color:"#C7C7C7",fontSize:10,lineHeight:17,marginTop:4,textAlign:"right"},headRow:{flexDirection:"row-reverse",justifyContent:"space-between",alignItems:"baseline",marginBottom:9,marginTop:3},headTitle:{fontSize:15,fontWeight:"900",color:"#111",textAlign:"right"},headMeta:{fontSize:9,color:"#999"},typeRow:{gap:9,paddingBottom:6},typeCard:{width:125,backgroundColor:"#FFF",borderRadius:16,padding:12,borderWidth:1,borderColor:"#E7E7EA"},typeIcon:{width:36,height:36,borderRadius:11,backgroundColor:"#FFF0F3",alignItems:"center",justifyContent:"center",marginBottom:8},typeTitle:{fontSize:11,fontWeight:"900",color:"#111",textAlign:"right"},typeHint:{fontSize:9,color:"#888",marginTop:2,textAlign:"right"},card:{backgroundColor:"#FFF",borderRadius:16,padding:12,borderWidth:1,borderColor:"#E7E7EA",marginBottom:9},selected:{borderColor:"#111"},cardMain:{flexDirection:"row-reverse",alignItems:"center"},iconBox:{width:42,height:42,borderRadius:13,backgroundColor:"#FFF0F3",alignItems:"center",justifyContent:"center"},iconBoxActive:{backgroundColor:"#111"},cardCopy:{flex:1,alignItems:"flex-end",paddingHorizontal:10},cardTitle:{fontSize:13,fontWeight:"900",color:"#222"},cardMeta:{fontSize:9,color:"#999",marginTop:3},actionRow:{flexDirection:"row-reverse",alignItems:"center",gap:7,borderTopWidth:1,borderColor:"#F1F1F2",marginTop:9,paddingTop:9},editPill:{flexDirection:"row-reverse",alignItems:"center",gap:5,backgroundColor:"#F4F4F5",paddingHorizontal:11,paddingVertical:7,borderRadius:10},editText:{fontSize:10,fontWeight:"800",color:"#222"},arrow:{width:34,height:34,borderRadius:10,backgroundColor:"#F7F7F8",alignItems:"center",justifyContent:"center"},deletePill:{marginLeft:"auto",flexDirection:"row-reverse",alignItems:"center",gap:4,backgroundColor:"#FFF1F0",paddingHorizontal:10,paddingVertical:7,borderRadius:10},deleteText:{fontSize:10,fontWeight:"800",color:"#B42318"},empty:{backgroundColor:"#FFF",borderRadius:18,padding:38,alignItems:"center",borderWidth:1,borderColor:"#E8E8EA"},emptyTitle:{fontSize:15,fontWeight:"900",color:"#222",marginTop:9},emptyText:{fontSize:10,color:"#888",textAlign:"center",marginTop:4},editor:{backgroundColor:"#FFF",borderRadius:18,padding:15,borderWidth:1,borderColor:"#E3E3E6",marginTop:4},editorHead:{flexDirection:"row",justifyContent:"space-between",alignItems:"center",marginBottom:14},editorTitle:{fontSize:16,fontWeight:"900",color:"#111",textAlign:"right"},editorSub:{fontSize:10,color:"#888",marginTop:2,textAlign:"right"},liveBadge:{flexDirection:"row-reverse",alignItems:"center",gap:5,backgroundColor:"#ECFDF3",paddingHorizontal:9,paddingVertical:6,borderRadius:12},dot:{width:6,height:6,borderRadius:3,backgroundColor:"#16A34A"},liveText:{fontSize:9,fontWeight:"800",color:"#166534"},label:{fontSize:11,fontWeight:"800",color:"#4B4B4B",textAlign:"right",marginBottom:6},input:{backgroundColor:"#F8F8F9",borderWidth:1,borderColor:"#E1E1E4",borderRadius:11,padding:12,color:"#111",fontSize:12,marginBottom:11},visibility:{backgroundColor:"#F8F8F9",borderRadius:12,padding:11,flexDirection:"row-reverse",alignItems:"center",justifyContent:"space-between",marginBottom:11},visibilityTitle:{fontSize:11,fontWeight:"800",color:"#222",textAlign:"right"},visibilityHint:{fontSize:9,color:"#888",marginTop:2,textAlign:"right"},mediaButton:{height:47,borderRadius:12,borderWidth:1,borderColor:"#F0B0BE",backgroundColor:"#FFF7F9",alignItems:"center",justifyContent:"center",flexDirection:"row-reverse",gap:7,marginBottom:9},mediaText:{fontSize:11,fontWeight:"900",color:"#B42318"},mediaItem:{backgroundColor:"#FAFAFA",borderRadius:12,padding:9,flexDirection:"row",alignItems:"center",gap:9,marginBottom:8},thumb:{width:58,height:58,borderRadius:10},thumbPlaceholder:{width:58,height:58,borderRadius:10,backgroundColor:"#F0F0F1",alignItems:"center",justifyContent:"center"},bannerThumb:{width:100,height:58,borderRadius:10,backgroundColor:"#EEE"},mediaCopy:{flex:1,alignItems:"flex-end"},mediaTitle:{fontSize:11,fontWeight:"800",color:"#333"},removeText:{fontSize:10,fontWeight:"900",color:"#B42318",marginTop:5},smallInput:{width:"100%",backgroundColor:"#FFF",borderWidth:1,borderColor:"#E2E2E5",borderRadius:9,padding:9,fontSize:11,color:"#111"},choiceRow:{gap:8,paddingBottom:8},choice:{paddingHorizontal:13,paddingVertical:8,borderRadius:18,backgroundColor:"#F1F1F2"},choiceActive:{backgroundColor:"#111"},choiceText:{fontSize:10,fontWeight:"800",color:"#555"},choiceActiveText:{fontSize:10,fontWeight:"800",color:"#FFF"},save:{height:50,borderRadius:13,backgroundColor:"#E11D48",alignItems:"center",justifyContent:"center",flexDirection:"row-reverse",gap:7,marginTop:10},saveText:{fontSize:12,fontWeight:"900",color:"#FFF"}
});
