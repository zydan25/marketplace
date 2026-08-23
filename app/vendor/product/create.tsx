import { useEffect, useState } from "react";
import * as ImagePicker from "expo-image-picker";
import { ActivityIndicator, Alert, Image, ScrollView, StyleSheet, Switch, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ScreenContainer } from "@/components/screen-container";
import { djangoApi } from "@/lib/django-api";

type Product = { id: number; name: string; sku: string; description?: string; brand?: string; material?: string; shipping_note?: string; return_policy?: string; price: string; sale_price?: string | null; effective_price: string; stock: number; currency: string; colors?: { name: string; hex?: string }[]; sizes?: { label: string; stock?: number }[]; hashtags?: string[]; variants?: { id: number; sku: string; color?: string; size?: string; price_override?: string | null; stock: number }[]; details?: Record<string, string> | string; is_trending: boolean; is_published: boolean; main_image_url?: string | null; gallery?: { id: number; url: string; is_primary?: boolean }[] };

const emptyForm = { name: "", sku: "", brand: "", material: "", description: "", details: "", price: "", salePrice: "", stock: "", shipping: "", returns: "", colors: "", sizes: "", variants: "", hashtags: "", isTrending: false, isPublished: true };
type FormState = typeof emptyForm;

export default function VendorProductCreateScreen() {
  const { edit } = useLocalSearchParams<{ edit?: string }>();
  const editingId = edit ? Number(edit) : null;
  
  const [loading, setLoading] = useState(!!editingId);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [imageData, setImageData] = useState<string[]>([]);
  const [existingImages, setExistingImages] = useState<{ id: number; url: string }[]>([]);
  const [saving, setSaving] = useState(false);
  const [formSection, setFormSection] = useState<"basic" | "pricing" | "variants" | "media">("basic");

  useEffect(() => {
    if (!editingId) return;
    async function loadProduct() {
      try {
        const product = await djangoApi<Product>(`/api/products/${editingId}/`);
        const details = typeof product.details === "string" ? product.details : Object.entries(product.details ?? {}).map(([key, value]) => `${key}: ${value}`).join("\n");
        setForm({ name: product.name, sku: product.sku, brand: product.brand ?? "", material: product.material ?? "", description: product.description ?? "", details, price: String(product.price ?? ""), salePrice: String(product.sale_price ?? ""), stock: String(product.stock ?? ""), shipping: product.shipping_note ?? "", returns: product.return_policy ?? "", colors: (product.colors ?? []).map(color => `${color.name}:${color.hex ?? "#E5E5E5"}`).join(","), sizes: (product.sizes ?? []).map(size => `${size.label}:${size.stock ?? product.stock}`).join(","), variants: (product.variants ?? []).map(variant => `${variant.sku}|${variant.color ?? ""}|${variant.size ?? ""}|${variant.price_override ?? ""}|${variant.stock}`).join("\n"), hashtags: (product.hashtags ?? []).join(","), isTrending: product.is_trending, isPublished: product.is_published });
        setExistingImages((product.gallery ?? []).filter(image => image.id > 0));
      } catch (error) {
        Alert.alert("خطأ", "تعذر تحميل بيانات المنتج.");
        router.back();
      } finally {
        setLoading(false);
      }
    }
    loadProduct();
  }, [editingId]);

  const setField = (key: keyof FormState, value: string | boolean) => setForm(current => ({ ...current, [key]: value }));
  const parseColors = () => form.colors.split(",").map((value, index) => { const [name, hex] = value.split(":"); return { name: (name || `لون ${index + 1}`).trim(), hex: (hex || "#E5E5E5").trim() }; }).filter(item => item.name);
  const parseSizes = () => form.sizes.split(",").map((value, index) => { const [label, stock] = value.split(":"); return { label: (label || `مقاس ${index + 1}`).trim(), stock: Number(stock || form.stock || 0) }; }).filter(item => item.label);
  const parseVariants = () => form.variants.split("\n").map((line, index) => { const [sku, color, size, price, stock] = line.split("|").map(item => item?.trim()); return { sku: sku || `${form.sku}-${index + 1}`, color: color || "", size: size || "", price_override: price || null, stock: Number(stock || form.stock || 0) }; }).filter(item => item.sku);

  async function pickImages() {
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], allowsMultipleSelection: true, quality: 0.78, base64: true });
    if (result.canceled) return;
    const encoded = result.assets.filter(asset => asset.base64).map(asset => `data:${asset.mimeType ?? "image/jpeg"};base64,${asset.base64}`);
    setImageData(current => [...current, ...encoded].slice(0, 8));
  }

  async function save() {
    if (!form.name.trim() || !form.sku.trim() || !form.price || !form.stock) return Alert.alert("بيانات ناقصة", "أكمل الاسم ورقم الصنف والسعر والمخزون.");
    setSaving(true);
    const details = form.details.split("\n").filter(Boolean).reduce<Record<string, string>>((acc, line, index) => { const [key, ...rest] = line.split(":"); acc[(key || `تفصيل ${index + 1}`).trim()] = rest.join(":").trim() || line.trim(); return acc; }, {});
    const payload = { name: form.name.trim(), sku: form.sku.trim(), slug: `${form.sku.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-${Date.now()}`, brand: form.brand.trim(), material: form.material.trim(), description: form.description.trim(), details, price: form.price, sale_price: form.salePrice || null, stock: Number(form.stock), shipping_note: form.shipping.trim(), return_policy: form.returns.trim(), colors: parseColors(), sizes: parseSizes(), hashtags: form.hashtags.split(",").map(item => item.trim()).filter(Boolean), variants: parseVariants(), keep_image_ids: existingImages.map(image => image.id), image_data_urls: imageData, is_published: form.isPublished, is_trending: form.isTrending, currency: "YER" };
    try { 
      await djangoApi(editingId ? `/api/products/${editingId}/` : "/api/products/", { method: editingId ? "PATCH" : "POST", body: JSON.stringify(payload) }); 
      Alert.alert("تم الحفظ", editingId ? "تم تحديث بيانات المنتج." : "تمت إضافة المنتج بنجاح.");
      router.replace("/vendor/products" as never);
    } catch (error) { 
      Alert.alert("تعذر الحفظ", error instanceof Error ? error.message : "تحقق من البيانات والصور."); 
    } finally { 
      setSaving(false); 
    }
  }

  const input = (key: keyof FormState, placeholder: string, multiline = false) => <TextInput style={[styles.input, multiline && styles.multiline]} placeholder={placeholder} placeholderTextColor="#999" value={String(form[key])} onChangeText={value => setField(key, value)} multiline={multiline} textAlign="right" />;

  return (
    <ScreenContainer className="bg-[#F7F7F7]" edges={["top", "bottom", "left", "right"]}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.headerBtn}>
          <MaterialIcons name="close" size={24} color="#111" />
        </TouchableOpacity>
        <Text style={styles.title}>{editingId ? "تعديل المنتج" : "إضافة منتج جديد"}</Text>
        <View style={{ width: 40 }} />
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator color="#E60023" size="large" />
        </View>
      ) : (
        <ScrollView style={styles.formScroll} contentContainerStyle={styles.form} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator>
          <FormSteps active={formSection} onChange={setFormSection} />
          
          {formSection === "basic" ? <>{input("name", "اسم المنتج بالعربية أو الإنجليزية")}{input("sku", "رقم الصنف SKU")}{input("brand", "العلامة التجارية")}{input("material", "الخامة / التركيب")}{input("description", "وصف المنتج الكامل", true)}{input("details", "تفاصيل إضافية، كل سطر: الخاصية: القيمة", true)}</> : null}
          {formSection === "pricing" ? <><View style={styles.row}>{input("price", "السعر الأصلي")}{input("salePrice", "سعر التخفيض")}</View><View style={styles.row}>{input("stock", "المخزون")}{input("shipping", "ملاحظة الشحن")}</View>{input("returns", "سياسة الإرجاع")}</> : null}
          {formSection === "variants" ? <>{input("colors", "الألوان: أزرق:#223366, أحمر:#AA2233")}{input("sizes", "المقاسات: S:10, M:20, L:15")}{input("variants", "الأصناف المتعددة، كل سطر: SKU|اللون|المقاس|السعر|المخزون", true)}{input("hashtags", "الوسوم: ترند, فستان, جديد")}</> : null}
          {formSection === "media" ? <>{existingImages.length ? <View style={styles.existingBox}><Text style={styles.existingTitle}>صور المنتج الحالية — اضغط لحذفها</Text><ScrollView horizontal contentContainerStyle={styles.previewRow}>{existingImages.map(image => <View key={image.id} style={styles.existingImage}><Image source={{ uri: image.url }} style={styles.preview} /><TouchableOpacity style={styles.removeImage} onPress={() => setExistingImages(current => current.filter(item => item.id !== image.id))}><MaterialIcons name="close" size={16} color="#FFF" /></TouchableOpacity></View>)}</ScrollView></View> : null}<TouchableOpacity style={styles.imagePicker} onPress={pickImages}><MaterialIcons name="add-photo-alternate" size={24} color="#E60023" /><Text style={styles.imagePickerText}>إضافة صور المنتج ({imageData.length}/8)</Text></TouchableOpacity><ScrollView horizontal contentContainerStyle={styles.previewRow}>{imageData.map((uri, index) => <Image key={index} source={{ uri }} style={styles.preview} />)}</ScrollView></> : null}
          
          <View style={styles.switchRow}>
            <Text style={styles.switchText}>عرض المنتج للعملاء فورًا</Text>
            <Switch value={form.isPublished} onValueChange={value => setField("isPublished", value)} trackColor={{ true: "#168451" }} />
          </View>
          <View style={styles.switchRow}>
            <Text style={styles.switchText}>إظهاره ضمن الترندات</Text>
            <Switch value={form.isTrending} onValueChange={value => setField("isTrending", value)} trackColor={{ true: "#E60023" }} />
          </View>
          
          <TouchableOpacity style={styles.save} onPress={save} disabled={saving}>
            {saving ? <ActivityIndicator color="#FFF" /> : <Text style={styles.saveText}>{editingId ? "حفظ التعديلات" : "إضافة ونشر المنتج"}</Text>}
          </TouchableOpacity>
        </ScrollView>
      )}
    </ScreenContainer>
  );
}

function FormSteps({ active, onChange }: { active: "basic" | "pricing" | "variants" | "media"; onChange: (value: "basic" | "pricing" | "variants" | "media") => void }) {
  const steps = [{ id: "basic" as const, label: "الأساسيات" }, { id: "pricing" as const, label: "السعر والشحن" }, { id: "variants" as const, label: "الألوان والأصناف" }, { id: "media" as const, label: "الصور والنشر" }];
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.stepList}>
      {steps.map(step => (
        <TouchableOpacity key={step.id} onPress={() => onChange(step.id)} style={[styles.step, active === step.id && styles.stepActive]}>
          <Text style={[styles.stepText, active === step.id && styles.stepTextActive]}>{step.label}</Text>
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  header: { height: 60, paddingHorizontal: 16, flexDirection: "row-reverse", justifyContent: "space-between", alignItems: "center", backgroundColor: "#FFF", borderBottomWidth: 1, borderColor: "#EEE" },
  headerBtn: { padding: 8 },
  title: { fontSize: 18, fontWeight: "900", color: "#111" },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  formScroll: { flex: 1, backgroundColor: "#F7F7F7" },
  form: { flexGrow: 1, padding: 16, paddingBottom: 100 },
  stepList: { gap: 8, paddingBottom: 16 },
  step: { paddingHorizontal: 16, paddingVertical: 10, borderRadius: 20, backgroundColor: "#FFF", borderWidth: 1, borderColor: "#E5E5E5" },
  stepActive: { backgroundColor: "#111", borderColor: "#111" },
  stepText: { color: "#777", fontSize: 12, fontWeight: "800" },
  stepTextActive: { color: "#FFF" },
  input: { backgroundColor: "#FFF", borderWidth: 1, borderColor: "#E5E5E5", borderRadius: 10, padding: 14, marginBottom: 12, fontSize: 14, color: "#111", flex: 1, minWidth: 0 },
  multiline: { minHeight: 100, textAlignVertical: "top" },
  row: { flexDirection: "row-reverse", gap: 12 },
  imagePicker: { flexDirection: "row-reverse", alignItems: "center", justifyContent: "center", gap: 8, padding: 16, borderRadius: 10, borderWidth: 1, borderColor: "#F1B4BB", backgroundColor: "#FFF7F8", marginBottom: 12 },
  imagePickerText: { color: "#B00020", fontWeight: "800", fontSize: 14 },
  previewRow: { gap: 8, paddingVertical: 10 },
  preview: { width: 80, height: 80, borderRadius: 8, backgroundColor: "#EEE" },
  existingBox: { backgroundColor: "#FFF", padding: 12, borderRadius: 10, marginBottom: 12, borderWidth: 1, borderColor: "#EEE" },
  existingTitle: { textAlign: "right", fontSize: 12, color: "#555", fontWeight: "800", marginBottom: 8 },
  existingImage: { position: "relative" },
  removeImage: { position: "absolute", top: 4, right: 4, width: 24, height: 24, borderRadius: 12, backgroundColor: "#E60023", alignItems: "center", justifyContent: "center" },
  switchRow: { flexDirection: "row-reverse", alignItems: "center", justifyContent: "space-between", backgroundColor: "#FFF", padding: 14, borderRadius: 10, marginBottom: 12, borderWidth: 1, borderColor: "#EEE" },
  switchText: { fontSize: 14, fontWeight: "800", color: "#333" },
  save: { backgroundColor: "#111", padding: 16, borderRadius: 10, alignItems: "center", marginTop: 12 },
  saveText: { color: "#FFF", fontWeight: "900", fontSize: 16 },
});
