import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import * as ImagePicker from "expo-image-picker";
import { useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Alert, Image, Modal, ScrollView, StyleSheet, Switch, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";

import { ScreenContainer } from "@/components/screen-container";
import { djangoApi } from "@/lib/django-api";

type CatalogNode = { id: number; name: string; slug: string; parent?: number | null; children?: CatalogNode[] };
type CatalogOption = { id: number; group: string; name: string; slug: string; category?: number | null; category_name?: string | null };
type Product = { id: number; name: string; sku: string; description?: string; brand?: string; material?: string; shipping_note?: string; return_policy?: string; price: string; sale_price?: string | null; stock: number; currency: string; colors?: { name: string; hex?: string }[]; sizes?: { label: string; stock?: number }[]; hashtags?: string[]; details?: Record<string, any> | string; is_trending: boolean; is_published: boolean; categories?: { id: number; name: string; parent?: number | null }[]; gallery?: { id: number; url: string }[] };
type ColorValue = { name: string; hex: string };

type FormState = { name: string; sku: string; brand: string; material: string; description: string; price: string; salePrice: string; stock: string; shipping: string; returns: string; hashtags: string; isTrending: boolean; isPublished: boolean };
const EMPTY_FORM: FormState = { name: "", sku: "", brand: "", material: "", description: "", price: "", salePrice: "", stock: "", shipping: "", returns: "", hashtags: "", isTrending: false, isPublished: true };
const PALETTE: ColorValue[] = [
  { name: "أسود", hex: "#111111" }, { name: "أبيض", hex: "#FFFFFF" }, { name: "أحمر", hex: "#D72638" }, { name: "أزرق", hex: "#2563EB" },
  { name: "أخضر", hex: "#168451" }, { name: "أصفر", hex: "#F2B600" }, { name: "برتقالي", hex: "#F97316" }, { name: "وردي", hex: "#EC4899" },
  { name: "بنفسجي", hex: "#8B5CF6" }, { name: "بني", hex: "#8B5E3C" }, { name: "رمادي", hex: "#777777" }, { name: "ذهبي", hex: "#C69A3B" },
];
const SIZES = ["XS", "S", "M", "L", "XL", "XXL", "28", "30", "32", "34", "36", "38", "40", "42", "44", "مقاس موحد"];

export default function VendorProductCreateScreen() {
  const { edit } = useLocalSearchParams<{ edit?: string }>();
  const editingId = edit ? Number(edit) : null;
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [categories, setCategories] = useState<CatalogNode[]>([]);
  const [options, setOptions] = useState<Record<string, CatalogOption[]>>({});
  const [selectedRoot, setSelectedRoot] = useState<number | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<number | null>(null);
  const [condition, setCondition] = useState("جديد");
  const [warranty, setWarranty] = useState("لا");
  const [warrantyDuration, setWarrantyDuration] = useState("");
  const [gender, setGender] = useState("");
  const [colors, setColors] = useState<ColorValue[]>([]);
  const [sizes, setSizes] = useState<string[]>([]);
  const [colorModal, setColorModal] = useState(false);
  const [customColorName, setCustomColorName] = useState("");
  const [customColorHex, setCustomColorHex] = useState("#E60023");
  const [customBrand, setCustomBrand] = useState("");
  const [showCustomBrand, setShowCustomBrand] = useState(false);
  const [customCategoryName, setCustomCategoryName] = useState("");
  const [imageData, setImageData] = useState<string[]>([]);
  const [existingImages, setExistingImages] = useState<{ id: number; url: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [step, setStep] = useState<"catalog" | "basic" | "variants" | "media">("catalog");

  useEffect(() => {
    (async () => {
      try {
        const tree = await djangoApi<{ categories: CatalogNode[]; options: Record<string, CatalogOption[]> }>("/api/catalog/tree/");
        setCategories(tree.categories ?? []);
        setOptions(tree.options ?? {});
        if (editingId) {
          const product = await djangoApi<Product>(`/api/products/${editingId}/`);
          const details: Record<string, any> = typeof product.details === "string" ? {} : (product.details ?? {});
          const leaf = product.categories?.[product.categories.length - 1];
          setSelectedCategory(leaf?.id ?? null);
          setSelectedRoot(leaf?.parent ?? null);
          setCondition(String(details.condition ?? "جديد"));
          setWarranty(String(details.warranty ?? "لا"));
          setWarrantyDuration(String(details.warranty_duration ?? ""));
          setGender(String(details.gender ?? ""));
          setCustomCategoryName(String(details.custom_category_name ?? ""));
          setForm({ name: product.name, sku: product.sku, brand: product.brand ?? "", material: product.material ?? "", description: product.description ?? "", price: String(product.price ?? ""), salePrice: String(product.sale_price ?? ""), stock: String(product.stock ?? ""), shipping: product.shipping_note ?? "", returns: product.return_policy ?? "", hashtags: (product.hashtags ?? []).join(","), isTrending: product.is_trending, isPublished: product.is_published });
          setColors((product.colors ?? []).map((color) => ({ name: color.name, hex: color.hex ?? "#111111" })));
          setSizes((product.sizes ?? []).map((item) => item.label));
          setExistingImages((product.gallery ?? []).filter((item) => item.id > 0));
        }
      } catch (error) { Alert.alert("تعذر تحميل نموذج المنتج", error instanceof Error ? error.message : "حاول مرة أخرى."); }
      finally { setLoading(false); }
    })();
  }, [editingId]);

  const children = useMemo(() => categories.find((item) => item.id === selectedRoot)?.children ?? [], [categories, selectedRoot]);
  const selectedCategoryName = [...categories, ...categories.flatMap((item) => item.children ?? [])].find((item) => item.id === selectedCategory)?.name ?? "";
  const brandOptions = (options.brand ?? []).filter((item) => !item.category || item.category === selectedCategory);
  const materialOptions = options.material ?? [];
  const genderOptions = options.gender ?? [];
  const conditionOptions = options.condition ?? [];
  const warrantyOptions = options.warranty ?? [];
  const clothingRoot = categories.find((item) => item.id === selectedRoot)?.name === "الملابس";
  const setField = (key: keyof FormState, value: string | boolean) => setForm((current) => ({ ...current, [key]: value }));

  function toggleColor(color: ColorValue) {
    setColors((current) => current.some((item) => item.hex.toLowerCase() === color.hex.toLowerCase()) ? current.filter((item) => item.hex.toLowerCase() !== color.hex.toLowerCase()) : [...current, color]);
  }
  function addCustomColor() {
    const hex = /^#[0-9a-fA-F]{6}$/.test(customColorHex.trim()) ? customColorHex.trim().toUpperCase() : "#E60023";
    const name = customColorName.trim() || "لون مخصص";
    setColors((current) => current.some((item) => item.hex.toLowerCase() === hex.toLowerCase()) ? current : [...current, { name, hex }]);
    setCustomColorName(""); setColorModal(false);
  }
  async function saveCustomBrand() {
    const value = customBrand.trim(); if (!value) return Alert.alert("اسم الشركة مطلوب", "اكتب اسم الشركة الجديدة.");
    try {
      const option = await djangoApi<CatalogOption>("/api/catalog-options/", { method: "POST", body: JSON.stringify({ group: "brand", name: value, category: selectedCategory, is_active: true }) });
      setOptions((current) => ({ ...current, brand: [...(current.brand ?? []), option] }));
      setField("brand", value); setCustomBrand(""); setShowCustomBrand(false);
    } catch (error) { Alert.alert("تعذر إضافة الشركة", error instanceof Error ? error.message : "لا يمكن حفظ الشركة."); }
  }
  async function pickImages() {
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], allowsMultipleSelection: true, quality: 0.8, base64: true });
    if (result.canceled) return;
    setImageData((current) => [...current, ...result.assets.filter((asset) => asset.base64).map((asset) => `data:${asset.mimeType ?? "image/jpeg"};base64,${asset.base64}`)].slice(0, 8));
  }
  async function save() {
    if (!form.name.trim() || !form.sku.trim() || !form.price || !form.stock) return Alert.alert("بيانات ناقصة", "أكمل الاسم ورقم الصنف والسعر والمخزون.");
    if (!selectedCategory && !customCategoryName.trim()) return Alert.alert("الفئة مطلوبة", "اختر الفئة العامة والفرعية، أو استخدم أخرى.");
    setSaving(true);
    const details = { condition, warranty, warranty_duration: warranty === "نعم" ? warrantyDuration.trim() : "", gender, category_root_id: selectedRoot, category_id: selectedCategory, category_name: selectedCategoryName, custom_category_name: customCategoryName.trim() };
    const payload: any = {
      name: form.name.trim(), sku: form.sku.trim(), slug: `${form.sku.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-${Date.now()}`,
      brand: form.brand.trim(), material: form.material.trim(), description: form.description.trim(), details,
      price: form.price, sale_price: form.salePrice || null, stock: Number(form.stock), shipping_note: form.shipping.trim(), return_policy: form.returns.trim(),
      colors, sizes: sizes.map((label) => ({ label, stock: Number(form.stock) || 0 })), hashtags: form.hashtags.split(",").map((item) => item.trim()).filter(Boolean),
      keep_image_ids: existingImages.map((item) => item.id), image_data_urls: imageData,
      is_published: form.isPublished, is_trending: form.isTrending, currency: "YER", category_ids: selectedCategory ? [selectedRoot, selectedCategory].filter(Boolean) : [],
    };
    try { await djangoApi(editingId ? `/api/products/${editingId}/` : "/api/products/", { method: editingId ? "PATCH" : "POST", body: JSON.stringify(payload) }); Alert.alert("تم الحفظ", editingId ? "تم تحديث المنتج." : "تمت إضافة المنتج بنجاح."); router.replace("/vendor/products" as never); }
    catch (error) { Alert.alert("تعذر الحفظ", error instanceof Error ? error.message : "تحقق من البيانات."); }
    finally { setSaving(false); }
  }

  if (loading) return <ScreenContainer><View style={styles.center}><ActivityIndicator color="#E60023" /></View></ScreenContainer>;
  return <ScreenContainer className="bg-[#F7F7F7]" edges={["top", "bottom", "left", "right"]}>
    <View style={styles.header}><TouchableOpacity onPress={() => router.back()}><MaterialIcons name="close" size={24} color="#111" /></TouchableOpacity><Text style={styles.headerTitle}>{editingId ? "تعديل المنتج" : "إضافة منتج"}</Text><View style={{ width: 24 }} /></View>
    <ScrollView style={{ flex: 1 }} contentContainerStyle={styles.form} keyboardShouldPersistTaps="handled">
      <StepRow active={step} onChange={setStep} />
      {step === "catalog" ? <View>
        <FieldTitle text="الفئة العامة" /><ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>{categories.map((item) => <Chip key={item.id} label={item.name} active={selectedRoot === item.id} onPress={() => { setSelectedRoot(item.id); setSelectedCategory(null); }} />)}</ScrollView>
        {selectedRoot ? <><FieldTitle text="الفئة الفرعية" /><ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>{children.map((item) => <Chip key={item.id} label={item.name} active={selectedCategory === item.id} onPress={() => setSelectedCategory(item.id)} />)}<Chip label="أخرى" active={!selectedCategory && !!customCategoryName} onPress={() => { setSelectedCategory(null); }} /></ScrollView></> : null}
        {!selectedCategory && selectedRoot ? <TextInput value={customCategoryName} onChangeText={setCustomCategoryName} placeholder="اسم التصنيف غير الموجود" placeholderTextColor="#999" style={styles.input} textAlign="right" /> : null}
        <FieldTitle text="حالة المنتج" /><View style={styles.wrap}>{conditionOptions.map((item) => <Chip key={item.id} label={item.name} active={condition === item.name} onPress={() => setCondition(item.name)} />)}</View>
        <View style={styles.info}><MaterialIcons name="category" size={19} color="#168451" /><Text style={styles.infoText}>التصنيف يحدد طريقة ظهور المنتج والفلترة والخيارات المناسبة له.</Text></View>
      </View> : null}
      {step === "basic" ? <View>
        <FieldTitle text="البيانات الأساسية" />{field("name", "اسم المنتج")}{field("sku", "رقم الصنف SKU")}
        <FieldTitle text="الشركة / العلامة التجارية" /><ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>{brandOptions.map((item) => <Chip key={item.id} label={item.name} active={form.brand === item.name} onPress={() => setField("brand", item.name)} />)}<Chip label="شركة أخرى" active={showCustomBrand} onPress={() => setShowCustomBrand((v) => !v)} /></ScrollView>
        {showCustomBrand ? <View style={styles.row}><TextInput value={customBrand} onChangeText={setCustomBrand} placeholder="اسم الشركة الجديدة" placeholderTextColor="#999" style={styles.input} textAlign="right" /><TouchableOpacity onPress={saveCustomBrand} style={styles.inlineAdd}><Text style={styles.inlineAddText}>إضافة</Text></TouchableOpacity></View> : null}
        <FieldTitle text="الخامة / التركيب" />{materialOptions.length ? <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>{materialOptions.map((item) => <Chip key={item.id} label={item.name} active={form.material === item.name} onPress={() => setField("material", item.name)} />)}</ScrollView> : null}{field("material", "الخامة")}
        {clothingRoot ? <><FieldTitle text="النوع" /><View style={styles.wrap}>{genderOptions.map((item) => <Chip key={item.id} label={item.name} active={gender === item.name} onPress={() => setGender(item.name)} />)}</View></> : null}
        {field("description", "وصف المنتج الكامل", true)}
      </View> : null}
      {step === "variants" ? <View>
        <FieldTitle text="الألوان" /><TouchableOpacity style={styles.colorChooser} onPress={() => setColorModal(true)}><View style={styles.colorPreviewRow}>{colors.slice(0, 6).map((color) => <View key={color.hex} style={[styles.colorDot, { backgroundColor: color.hex }]} />)}</View><View style={styles.colorChooserCopy}><Text style={styles.colorChooserTitle}>اختيار الألوان</Text><Text style={styles.colorChooserSub}>{colors.length ? `${colors.length} ألوان` : "اختر عدة ألوان"}</Text></View><MaterialIcons name="palette" size={23} color="#E60023" /></TouchableOpacity>
        <View style={styles.wrap}>{colors.map((color) => <View key={color.hex} style={styles.selectedColor}><View style={[styles.colorDot, { backgroundColor: color.hex }]} /><Text style={styles.selectedColorText}>{color.name}</Text><TouchableOpacity onPress={() => setColors((items) => items.filter((item) => item.hex !== color.hex))}><MaterialIcons name="close" size={15} color="#A00" /></TouchableOpacity></View>)}</View>
        <FieldTitle text="المقاسات" /><View style={styles.wrap}>{SIZES.map((size) => <Chip key={size} label={size} active={sizes.includes(size)} onPress={() => setSizes((current) => current.includes(size) ? current.filter((item) => item !== size) : [...current, size])} />)}</View>
        <FieldTitle text="السعر والمخزون" /><View style={styles.row}>{field("price", "السعر")}{field("salePrice", "سعر التخفيض")}</View><View style={styles.row}>{field("stock", "المخزون")}{field("shipping", "ملاحظة الشحن")}</View>
        <FieldTitle text="الضمان" /><View style={styles.wrap}>{warrantyOptions.map((item) => <Chip key={item.id} label={item.name} active={warranty === item.name} onPress={() => setWarranty(item.name)} />)}</View>{warranty === "نعم" ? <TextInput value={warrantyDuration} onChangeText={setWarrantyDuration} placeholder="مدة الضمان" placeholderTextColor="#999" style={styles.input} textAlign="right" /> : null}
        <FieldTitle text="الوسوم" />{field("hashtags", "مثال: هاتف, سامسونج, جديد")}
      </View> : null}
      {step === "media" ? <View>
        {existingImages.length ? <View style={styles.existing}><Text style={styles.label}>الصور الحالية</Text><ScrollView horizontal contentContainerStyle={styles.previewRow}>{existingImages.map((image) => <View key={image.id} style={styles.existingImage}><Image source={{ uri: image.url }} style={styles.preview} /><TouchableOpacity style={styles.remove} onPress={() => setExistingImages((items) => items.filter((item) => item.id !== image.id))}><MaterialIcons name="close" size={15} color="#FFF" /></TouchableOpacity></View>)}</ScrollView></View> : null}
        <TouchableOpacity style={styles.mediaButton} onPress={pickImages}><MaterialIcons name="add-photo-alternate" size={24} color="#E60023" /><Text style={styles.mediaText}>إضافة صور ({imageData.length}/8)</Text></TouchableOpacity><ScrollView horizontal contentContainerStyle={styles.previewRow}>{imageData.map((uri, index) => <Image key={index} source={{ uri }} style={styles.preview} />)}</ScrollView>
        <View style={styles.toggleRow}><Text style={styles.toggleText}>نشر المنتج للعملاء</Text><Switch value={form.isPublished} onValueChange={(v) => setField("isPublished", v)} trackColor={{ true: "#168451" }} /></View><View style={styles.toggleRow}><Text style={styles.toggleText}>إظهاره ضمن الترند</Text><Switch value={form.isTrending} onValueChange={(v) => setField("isTrending", v)} trackColor={{ true: "#E60023" }} /></View>
      </View> : null}
      <TouchableOpacity disabled={saving} onPress={save} style={styles.save}>{saving ? <ActivityIndicator color="#FFF" /> : <Text style={styles.saveText}>{editingId ? "حفظ التعديلات" : "إضافة المنتج"}</Text>}</TouchableOpacity>
    </ScrollView>
    <Modal visible={colorModal} transparent animationType="slide" onRequestClose={() => setColorModal(false)}><View style={styles.backdrop}><View style={styles.colorModal}><View style={styles.modalHeader}><Text style={styles.modalTitle}>ألوان المنتج</Text><TouchableOpacity onPress={() => setColorModal(false)}><MaterialIcons name="close" size={24} color="#111" /></TouchableOpacity></View><Text style={styles.modalHint}>اضغط على اللون لإضافته أو إزالته، ويمكن إدخال لون مخصص.</Text><View style={styles.palette}>{PALETTE.map((color) => <TouchableOpacity key={color.hex} onPress={() => toggleColor(color)} style={[styles.paletteItem, colors.some((item) => item.hex.toLowerCase() === color.hex.toLowerCase()) && styles.paletteActive]}><View style={[styles.paletteSwatch, { backgroundColor: color.hex }]} /><Text style={styles.paletteText}>{color.name}</Text></TouchableOpacity>)}</View><TextInput value={customColorName} onChangeText={setCustomColorName} placeholder="اسم اللون المخصص" placeholderTextColor="#999" style={styles.input} textAlign="right"/><View style={styles.row}><TextInput value={customColorHex} onChangeText={setCustomColorHex} placeholder="#RRGGBB" placeholderTextColor="#999" style={styles.input} textAlign="left" autoCapitalize="characters"/><TouchableOpacity onPress={addCustomColor} style={styles.customAdd}><View style={[styles.colorBig, { backgroundColor: /^#[0-9a-fA-F]{6}$/.test(customColorHex) ? customColorHex : "#E60023" }]} /><Text style={styles.customAddText}>إضافة</Text></TouchableOpacity></View><TouchableOpacity onPress={() => setColorModal(false)} style={styles.closeModal}><Text style={styles.saveText}>تم</Text></TouchableOpacity></View></View></Modal>
  </ScreenContainer>;

  function field(key: keyof FormState, placeholder: string, multiline = false) { return <TextInput value={String(form[key])} onChangeText={(value) => setField(key, value)} placeholder={placeholder} placeholderTextColor="#999" style={[styles.input, multiline && styles.multiline]} textAlign="right" multiline={multiline} />; }
}

function StepRow({ active, onChange }: { active: "catalog" | "basic" | "variants" | "media"; onChange: (value: "catalog" | "basic" | "variants" | "media") => void }) { const items = [{ id: "catalog" as const, label: "التصنيف" }, { id: "basic" as const, label: "البيانات" }, { id: "variants" as const, label: "الخيارات" }, { id: "media" as const, label: "الصور" }]; return <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.stepList}>{items.map((item) => <TouchableOpacity key={item.id} onPress={() => onChange(item.id)} style={[styles.step, active === item.id && styles.stepActive]}><Text style={[styles.stepText, active === item.id && styles.stepTextActive]}>{item.label}</Text></TouchableOpacity>)}</ScrollView>; }
function FieldTitle({ text }: { text: string }) { return <Text style={styles.fieldTitle}>{text}</Text>; }
function Chip({ label, active, onPress }: { label: string; active: boolean; onPress: () => void }) { return <TouchableOpacity onPress={onPress} style={[styles.chip, active && styles.chipActive]}><Text style={[styles.chipText, active && styles.chipTextActive]}>{label}</Text></TouchableOpacity>; }

const styles = StyleSheet.create({
  header: { height: 60, paddingHorizontal: 16, flexDirection: "row-reverse", justifyContent: "space-between", alignItems: "center", backgroundColor: "#FFF", borderBottomWidth: 1, borderColor: "#EEE" }, headerTitle: { fontSize: 18, fontWeight: "900", color: "#111" }, center: { flex: 1, justifyContent: "center", alignItems: "center" }, form: { padding: 14, paddingBottom: 110 },
  stepList: { gap: 8, paddingBottom: 15 }, step: { paddingHorizontal: 15, paddingVertical: 10, borderRadius: 18, backgroundColor: "#FFF", borderWidth: 1, borderColor: "#E3E3E3" }, stepActive: { backgroundColor: "#111", borderColor: "#111" }, stepText: { color: "#777", fontSize: 11, fontWeight: "800" }, stepTextActive: { color: "#FFF" }, fieldTitle: { color: "#222", fontSize: 12, fontWeight: "900", textAlign: "right", marginVertical: 7 }, chips: { gap: 7, paddingBottom: 4 }, wrap: { flexDirection: "row-reverse", flexWrap: "wrap", gap: 7, marginBottom: 8 }, chip: { paddingHorizontal: 12, paddingVertical: 9, borderRadius: 18, backgroundColor: "#FFF", borderWidth: 1, borderColor: "#E3E3E3" }, chipActive: { backgroundColor: "#111", borderColor: "#111" }, chipText: { color: "#555", fontSize: 11, fontWeight: "700" }, chipTextActive: { color: "#FFF" },
  input: { flex: 1, minWidth: 0, minHeight: 46, backgroundColor: "#FFF", borderWidth: 1, borderColor: "#E2E2E2", borderRadius: 10, paddingHorizontal: 12, paddingVertical: 11, color: "#111", fontSize: 13, marginBottom: 10 }, multiline: { minHeight: 95, textAlignVertical: "top" }, row: { flexDirection: "row-reverse", gap: 8 }, inlineAdd: { width: 74, height: 46, borderRadius: 10, backgroundColor: "#111", alignItems: "center", justifyContent: "center" }, inlineAddText: { color: "#FFF", fontWeight: "900" }, info: { flexDirection: "row-reverse", gap: 8, alignItems: "flex-start", backgroundColor: "#F7FBF8", borderWidth: 1, borderColor: "#DDEEE2", borderRadius: 10, padding: 11, marginTop: 10 }, infoText: { flex: 1, color: "#506056", textAlign: "right", fontSize: 10, lineHeight: 17 },
  colorChooser: { flexDirection: "row-reverse", alignItems: "center", gap: 10, padding: 12, backgroundColor: "#FFF", borderWidth: 1, borderColor: "#E4E4E4", borderRadius: 12 }, colorChooserCopy: { flex: 1, alignItems: "flex-end" }, colorChooserTitle: { color: "#111", fontWeight: "900", fontSize: 13 }, colorChooserSub: { color: "#888", fontSize: 10, marginTop: 3 }, colorPreviewRow: { flexDirection: "row-reverse", gap: 3, flexWrap: "wrap", maxWidth: 72 }, colorDot: { width: 24, height: 24, borderRadius: 12, borderWidth: 1, borderColor: "#DDD" }, selectedColor: { flexDirection: "row-reverse", alignItems: "center", gap: 7, backgroundColor: "#FFF", borderWidth: 1, borderColor: "#E4E4E4", borderRadius: 18, paddingHorizontal: 9, paddingVertical: 6 }, selectedColorText: { fontSize: 10, color: "#333", fontWeight: "800" },
  mediaButton: { flexDirection: "row-reverse", alignItems: "center", justifyContent: "center", gap: 8, backgroundColor: "#FFF7F8", borderWidth: 1, borderColor: "#F0B2B9", borderRadius: 10, padding: 14 }, mediaText: { color: "#A6001D", fontWeight: "900", fontSize: 12 }, previewRow: { gap: 8, paddingVertical: 10 }, preview: { width: 80, height: 80, borderRadius: 8, backgroundColor: "#EEE" }, existing: { backgroundColor: "#FFF", padding: 10, borderRadius: 10, marginBottom: 10 }, label: { color: "#555", textAlign: "right", fontSize: 11, fontWeight: "800" }, existingImage: { position: "relative" }, remove: { position: "absolute", top: 3, right: 3, width: 22, height: 22, borderRadius: 11, backgroundColor: "#D72638", alignItems: "center", justifyContent: "center" }, toggleRow: { marginTop: 8, backgroundColor: "#FFF", borderRadius: 9, padding: 10, flexDirection: "row-reverse", alignItems: "center", justifyContent: "space-between" }, toggleText: { fontSize: 12, fontWeight: "800", color: "#333" }, save: { height: 50, backgroundColor: "#E60023", borderRadius: 12, alignItems: "center", justifyContent: "center", marginTop: 15 }, saveText: { color: "#FFF", fontWeight: "900", fontSize: 13 },
  backdrop: { flex: 1, backgroundColor: "rgba(0,0,0,.45)", justifyContent: "flex-end" }, colorModal: { backgroundColor: "#FFF", padding: 16, borderTopLeftRadius: 22, borderTopRightRadius: 22, maxHeight: "90%" }, modalHeader: { flexDirection: "row-reverse", justifyContent: "space-between", alignItems: "center" }, modalTitle: { fontSize: 18, fontWeight: "900", color: "#111" }, modalHint: { color: "#777", fontSize: 10, textAlign: "right", marginVertical: 8 }, palette: { flexDirection: "row-reverse", flexWrap: "wrap", gap: 7 }, paletteItem: { width: "22%", alignItems: "center", borderWidth: 1, borderColor: "transparent", borderRadius: 9, paddingVertical: 7 }, paletteActive: { borderColor: "#111", backgroundColor: "#F7F7F7" }, paletteSwatch: { width: 34, height: 34, borderRadius: 17, borderWidth: 1, borderColor: "#DDD" }, paletteText: { color: "#444", fontSize: 9, marginTop: 3 }, customAdd: { width: 86, height: 46, backgroundColor: "#F7F7F7", borderRadius: 10, flexDirection: "row-reverse", alignItems: "center", justifyContent: "center", gap: 5 }, colorBig: { width: 26, height: 26, borderRadius: 13, borderWidth: 1, borderColor: "#DDD" }, customAddText: { fontSize: 10, fontWeight: "900", color: "#111" }, closeModal: { height: 46, backgroundColor: "#111", borderRadius: 10, alignItems: "center", justifyContent: "center", marginTop: 10 }
});