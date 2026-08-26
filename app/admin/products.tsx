import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import * as ImagePicker from "expo-image-picker";
import { Alert, FlatList, Image, ScrollView, StyleSheet, Switch, Text, TouchableOpacity, View } from "react-native";
import { useCallback, useEffect, useState } from "react";

import { AdminLayout, AdminField, AdminPageHeaderAction, AdminEmptyState, Colors, Font, Radius, Shadow, Spacing, showToast } from "@/components/admin";
import { useAuth } from "@/hooks/use-auth";
import { useCategories } from "@/hooks/use-categories";
import { createProduct, getAdminProducts, type ProductEditorPayload, type StoreProduct, updateProduct } from "@/lib/product-api";
import { getAdminStorefront } from "@/lib/storefront-api";
import { formatYER } from "@/lib/catalog";

type DraftImage = { dataUrl: string; fileName: string; sortOrder: number };
type FormState = { productCode: string; name: string; category: string; categoriesText: string; price: string; discountPercent: string; description: string; details: string; material: string; shippingNote: string; colorsText: string; sizesText: string; isTrending: boolean; trendTagsText: string; isPublished: boolean; };
const emptyForm: FormState = { productCode: "", name: "", category: "", categoriesText: "", price: "", discountPercent: "0", description: "", details: "", material: "", shippingNote: "", colorsText: "", sizesText: "", isTrending: false, trendTagsText: "", isPublished: true };

const parseColors = (value: string) => value.split("\n").map((line) => { const [name, hex] = line.split("|").map((part) => part?.trim()); return { name, hex }; }).filter((item): item is { name: string; hex: string } => Boolean(item.name && item.hex));
const parseSizes = (value: string) => value.split("\n").map((line) => { const [label, stock] = line.split("|").map((part) => part?.trim()); return { label, stock: Number(stock) || 0 }; }).filter((item): item is { label: string; stock: number } => Boolean(item.label));
const parseCategories = (value: string) => [...new Set(value.split(/[،,\n]/).map((item) => item.trim()).filter(Boolean))];

export default function AdminProductsScreen() {
  useAuth();
  const { categories: apiCategories } = useCategories();
  const [items, setItems] = useState<StoreProduct[]>([]); const [loading, setLoading] = useState(true); const [editing, setEditing] = useState<StoreProduct | null>(null); const [form, setForm] = useState<FormState>(emptyForm); const [newImages, setNewImages] = useState<DraftImage[]>([]); const [saving, setSaving] = useState(false); const [availableCategories, setAvailableCategories] = useState<string[]>([]);
  const load = useCallback(async () => { try { setLoading(true); const [products, storefront] = await Promise.all([getAdminProducts(), getAdminStorefront()]); setItems(products); setAvailableCategories([...new Set([...apiCategories.map((category) => category.name), ...storefront.flatMap((tab) => [tab.title, ...tab.circles.map((circle) => circle.targetCategory || circle.title)]).filter(Boolean)])]); } catch (error) { Alert.alert("تعذر تحميل الأصناف", error instanceof Error ? error.message : "حاولي مجددًا."); } finally { setLoading(false); } }, [apiCategories]);
  useEffect(() => { load(); }, [load]);
  const edit = (product?: StoreProduct) => { setEditing(product ?? null); setNewImages([]); setForm(product ? { productCode: product.productCode, name: product.name, category: product.category, categoriesText: (product.categories.length ? product.categories : [product.category]).join("، "), price: String(product.originalPrice), discountPercent: String(product.discountPercent), description: product.description, details: product.details, material: product.material, shippingNote: product.shippingNote, colorsText: product.colors.map((color) => `${color.name} | ${color.hex}`).join("\n"), sizesText: product.sizes.map((size) => `${size.label} | ${size.stock}`).join("\n"), isTrending: product.isTrending, trendTagsText: product.trendTags.map((tag) => `#${tag}`).join("، "), isPublished: true } : emptyForm); };
  const pickImages = async () => { const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], allowsEditing: true, aspect: [3, 4], quality: 1, base64: true }); if (result.canceled) return; const prepared = result.assets.filter((asset) => asset.base64).map((asset, index) => ({ dataUrl: `data:${asset.mimeType ?? "image/jpeg"};base64,${asset.base64}`, fileName: asset.fileName ?? `product-${Date.now()}-${index}.jpg`, sortOrder: newImages.length + index })); setNewImages((current) => [...current, ...prepared].slice(0, 10)); };
  const save = async () => { const price = Number(form.price); const discountPercent = Number(form.discountPercent); const categories = parseCategories(form.categoriesText || form.category); const trendTags = parseCategories(form.trendTagsText).map((tag) => tag.replace(/^#/, "")); if (!form.name.trim() || !categories.length || !form.description.trim() || !Number.isInteger(price) || price <= 0) { Alert.alert("بيانات ناقصة", "أدخلي الاسم وفئة واحدة على الأقل والوصف والسعر الصحيح."); return; } if (form.isTrending && !trendTags.length) { Alert.alert("اسم الترند مطلوب", "أضيفي هاشتاج ترند واحدًا على الأقل."); return; } const payload: ProductEditorPayload = { productCode: form.productCode.trim().toUpperCase() || undefined, categoryIds: apiCategories.filter((category) => categories.includes(category.name)).map((category) => category.id), name: form.name.trim(), category: categories[0], categories, description: form.description.trim(), details: form.details.trim(), material: form.material.trim(), price, discountPercent, shippingNote: form.shippingNote.trim(), isTrending: form.isTrending, trendTags, isPublished: form.isPublished, colors: parseColors(form.colorsText), sizes: parseSizes(form.sizesText), ...(editing ? { keepImageIds: editing.images.map((image) => Number(image.id)).filter((id) => id > 0), existingImages: editing.images.map((image, index) => ({ id: Number(image.id), storageKey: image.storageKey, url: image.url, sortOrder: index })), newImages } : { images: newImages }) }; try { setSaving(true); if (editing) await updateProduct(editing.id, payload); else await createProduct(payload); await load(); setEditing(null); setForm(emptyForm); setNewImages([]); showToast("تم حفظ الصنف بنجاح", "success"); } catch (error) { Alert.alert("تعذر حفظ الصنف", error instanceof Error ? error.message : "راجعي البيانات وحاولي مرة أخرى."); } finally { setSaving(false); } };

  if (editing || (!items.length && !loading)) {
    return (
      <AdminLayout title={editing ? "تعديل الصنف" : "إضافة صنف"}>
        <ScrollView style={{ flex: 1 }} contentContainerStyle={styles.formContent} showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">
          <Text style={styles.formIntro}>يُعرض الصنف في المتجر بعد الحفظ إذا كانت حالة النشر مفعّلة.</Text>
          <AdminField label="رقم الصنف" value={form.productCode} onChangeText={(productCode) => setForm((v) => ({ ...v, productCode }))} placeholder="مثال: TDS-2026-001" helper="اختياري؛ إن تركته فارغًا يُنشأ رقم فريد تلقائيًا." />
          <AdminField label="اسم الصنف" value={form.name} onChangeText={(name) => setForm((v) => ({ ...v, name }))} placeholder="مثال: فستان أطفال مطرز" />
          <AdminField label="الفئات والقوائم" value={form.categoriesText} onChangeText={(categoriesText) => setForm((v) => ({ ...v, categoriesText }))} placeholder="مثال: أطفال، بناتي" helper="يمكنك إضافة أكثر من فئة بالفاصلة، أو اختيارها من الأزرار." />
          <CategoryPicker choices={availableCategories} value={form.categoriesText} onChange={(categoriesText) => setForm((v) => ({ ...v, categoriesText }))} />
          <View style={styles.twoFields}>
            <AdminField compact label="السعر (ر.ي)" value={form.price} onChangeText={(price) => setForm((v) => ({ ...v, price }))} keyboardType="numeric" placeholder="0" />
            <AdminField compact label="نسبة الخصم %" value={form.discountPercent} onChangeText={(discountPercent) => setForm((v) => ({ ...v, discountPercent }))} keyboardType="numeric" placeholder="0" />
          </View>
          <View style={styles.trendRow}>
            <View style={{ flex: 1 }}>
              <Text style={styles.trendTitle}>إظهار الصنف في ترندات</Text>
              <Text style={styles.trendHint}>عند التفعيل يظهر الصنف تحت الهاشتاجات المحددة.</Text>
            </View>
            <Switch value={form.isTrending} onValueChange={(isTrending) => setForm((v) => ({ ...v, isTrending }))} trackColor={{ true: Colors.primary }} />
          </View>
          {form.isTrending && <AdminField label="هاشتاجات الترند" value={form.trendTagsText} onChangeText={(trendTagsText) => setForm((v) => ({ ...v, trendTagsText }))} placeholder="#فساتين #أزياء" helper="افصلي الهاشتاجات بالفاصلة أو سطر جديد." />}
          <AdminField label="الوصف" value={form.description} onChangeText={(description) => setForm((v) => ({ ...v, description }))} placeholder="وصف يظهر للعميل" multiline numberOfLines={3} />
          <AdminField label="التفاصيل" value={form.details} onChangeText={(details) => setForm((v) => ({ ...v, details }))} placeholder="مواصفات إضافية" multiline numberOfLines={3} />
          <AdminField label="المادة" value={form.material} onChangeText={(material) => setForm((v) => ({ ...v, material }))} placeholder="مثال: قطن 100%" />
          <AdminField label="ملاحظة الشحن" value={form.shippingNote} onChangeText={(shippingNote) => setForm((v) => ({ ...v, shippingNote }))} placeholder="تعليمات الشحن" />
          <AdminField label="الألوان" value={form.colorsText} onChangeText={(colorsText) => setForm((v) => ({ ...v, colorsText }))} placeholder="أحمر | #FF0000" multiline numberOfLines={3} helper="اسم اللون | الكود في كل سطر." />
          <AdminField label="المقاسات" value={form.sizesText} onChangeText={(sizesText) => setForm((v) => ({ ...v, sizesText }))} placeholder="S | 10" multiline numberOfLines={3} helper="المقاس | الكمية في كل سطر." />
          <Text style={styles.fieldLabel}>صور الصنف</Text>
          <View style={styles.imageGrid}>
            {editing?.images.map((image, index) => (
              <View key={`existing-${image.id}`} style={styles.imageWrap}>
                <Image source={{ uri: image.url }} style={styles.imageThumb} />
              </View>
            ))}
            {newImages.map((image, index) => (
              <View key={`new-${index}`} style={styles.imageWrap}>
                <Image source={{ uri: image.dataUrl }} style={styles.imageThumb} />
              </View>
            ))}
            {newImages.length + (editing?.images.length ?? 0) < 10 && (
              <TouchableOpacity style={styles.imageAdd} onPress={pickImages}>
                <MaterialIcons name="add-a-photo" size={22} color={Colors.textMuted} />
              </TouchableOpacity>
            )}
          </View>
          <View style={styles.trendRow}>
            <View style={{ flex: 1 }}>
              <Text style={styles.trendTitle}>حالة النشر</Text>
              <Text style={styles.trendHint}>عند التفعيل يظهر الصنف للعملاء.</Text>
            </View>
            <Switch value={form.isPublished} onValueChange={(isPublished) => setForm((v) => ({ ...v, isPublished }))} trackColor={{ true: Colors.primary }} />
          </View>
          <TouchableOpacity style={styles.saveBtn} onPress={save} disabled={saving}>
            <Text style={styles.saveBtnText}>{saving ? "جارِ الحفظ..." : editing ? "تحديث الصنف" : "إضافة الصنف"}</Text>
          </TouchableOpacity>
        </ScrollView>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout
      title="إدارة الأصناف"
      rightAction={<AdminPageHeaderAction icon="add-circle-outline" onPress={() => edit()} />}
    >
      <FlatList
        style={{ flex: 1 }}
        data={items}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.list}
        refreshing={loading}
        onRefresh={load}
        ListHeaderComponent={
          <TouchableOpacity style={styles.createCard} onPress={() => edit()} activeOpacity={0.7}>
            <View style={styles.createIcon}>
              <MaterialIcons name="add-shopping-cart" size={22} color={Colors.textInverse} />
            </View>
            <View style={styles.createCopy}>
              <Text style={styles.createTitle}>إضافة صنف جديد</Text>
              <Text style={styles.createText}>أضيفي التفاصيل والألوان والمقاسات والصور بشكل منفصل.</Text>
            </View>
          </TouchableOpacity>
        }
        renderItem={({ item }) => (
          <View style={styles.listItem}>
            <View style={styles.itemImage}>
              {item.images[0]?.url ? (
                <Image source={{ uri: item.images[0].url }} style={styles.itemPhoto} />
              ) : (
                <MaterialIcons name="image-not-supported" size={22} color={Colors.textMuted} />
              )}
            </View>
            <View style={styles.itemCopy}>
              <Text style={styles.itemName} numberOfLines={2}>{item.name}</Text>
              <Text style={styles.itemMeta}>{item.category} · {formatYER(item.price)}</Text>
              {item.discountPercent ? (
                <Text style={styles.itemDiscount}>خصم {item.discountPercent}%</Text>
              ) : null}
            </View>
            <TouchableOpacity style={styles.editBtn} onPress={() => edit(item)}>
              <Text style={styles.editBtnText}>تعديل</Text>
            </TouchableOpacity>
          </View>
        )}
        ListEmptyComponent={
          <AdminEmptyState
            icon="inventory-2"
            title="لا توجد أصناف"
            description="لم تتم إضافة أي أصناف حتى الآن."
            action={
              <TouchableOpacity style={styles.saveBtn} onPress={() => edit()}>
                <Text style={styles.saveBtnText}>+ إضافة صنف</Text>
              </TouchableOpacity>
            }
          />
        }
      />
    </AdminLayout>
  );
}

function CategoryPicker({ choices, value, onChange }: { choices: string[]; value: string; onChange: (value: string) => void }) {
  const selected = parseCategories(value);
  if (!choices.length) return null;
  return (
    <View style={styles.categoryPicker}>
      <Text style={styles.categoryPickerTitle}>اختيار سريع من قوائم المتجر</Text>
      <View style={styles.chipRow}>
        {choices.map((choice) => (
          <TouchableOpacity
            key={choice}
            onPress={() => onChange(selected.includes(choice) ? selected.filter((item) => item !== choice).join("، ") : [...selected, choice].join("، "))}
            style={[styles.chip, selected.includes(choice) && styles.chipActive]}
          >
            <Text style={[styles.chipText, selected.includes(choice) && styles.chipTextActive]}>{choice}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  list: { padding: Spacing.lg, paddingBottom: Spacing["4xl"] },
  formContent: { padding: Spacing.lg, paddingBottom: Spacing["4xl"] },
  formIntro: { color: Colors.textSecondary, ...Font.small, textAlign: "right", marginBottom: Spacing.lg },
  twoFields: { flexDirection: "row-reverse", gap: Spacing.md },

  /* Trend row */
  trendRow: { backgroundColor: Colors.surface, borderRadius: Radius.sm, borderWidth: 1, borderColor: Colors.border, padding: Spacing.md, flexDirection: "row-reverse", alignItems: "center", gap: Spacing.md, marginBottom: Spacing.lg },
  trendTitle: { color: Colors.text, ...Font.label, textAlign: "right" },
  trendHint: { color: Colors.textMuted, ...Font.tiny, textAlign: "right", marginTop: 2 },

  /* Category picker */
  categoryPicker: { backgroundColor: Colors.surface, borderRadius: Radius.sm, borderWidth: 1, borderColor: Colors.border, padding: Spacing.md, marginTop: -Spacing.sm, marginBottom: Spacing.lg },
  categoryPickerTitle: { color: Colors.textSecondary, ...Font.tiny, textAlign: "right", marginBottom: Spacing.sm },
  chipRow: { flexDirection: "row-reverse", flexWrap: "wrap", gap: Spacing.sm },
  chip: { borderRadius: Radius.sm, borderWidth: 1, borderColor: Colors.border, paddingHorizontal: Spacing.md, paddingVertical: Spacing.sm, backgroundColor: Colors.surface },
  chipActive: { backgroundColor: Colors.black, borderColor: Colors.black },
  chipText: { color: Colors.textSecondary, ...Font.chip },
  chipTextActive: { color: Colors.textInverse, fontWeight: "700" },

  /* Images */
  fieldLabel: { color: Colors.text, ...Font.label, textAlign: "right", marginBottom: Spacing.sm },
  imageGrid: { flexDirection: "row-reverse", flexWrap: "wrap", gap: Spacing.sm, marginBottom: Spacing.lg },
  imageWrap: { width: 80, height: 106, borderRadius: Radius.sm, overflow: "hidden", backgroundColor: Colors.surfaceAlt },
  imageThumb: { width: "100%", height: "100%", resizeMode: "cover" as const },
  imageAdd: { width: 80, height: 106, borderRadius: Radius.sm, borderWidth: 2, borderColor: Colors.border, borderStyle: "dashed" as const, alignItems: "center", justifyContent: "center", backgroundColor: Colors.surfaceAlt },

  /* Create card */
  createCard: { flexDirection: "row-reverse", alignItems: "center", backgroundColor: Colors.primary, borderRadius: Radius.md, padding: Spacing.lg, gap: Spacing.md, marginBottom: Spacing.lg, ...Shadow.raised },
  createIcon: { width: 44, height: 44, borderRadius: Radius.sm, backgroundColor: "rgba(255,255,255,0.2)", alignItems: "center", justifyContent: "center" },
  createCopy: { flex: 1 },
  createTitle: { color: Colors.textInverse, ...Font.cardTitle },
  createText: { color: "rgba(255,255,255,0.8)", ...Font.tiny, textAlign: "right", marginTop: 2 },

  /* List item */
  listItem: { flexDirection: "row-reverse", alignItems: "center", backgroundColor: Colors.surface, borderRadius: Radius.md, padding: Spacing.md, marginBottom: Spacing.sm, gap: Spacing.md, ...Shadow.soft },
  itemImage: { width: 60, height: 80, borderRadius: Radius.sm, overflow: "hidden", backgroundColor: Colors.surfaceAlt, alignItems: "center", justifyContent: "center" },
  itemPhoto: { width: "100%", height: "100%", resizeMode: "cover" as const },
  itemCopy: { flex: 1, alignItems: "flex-end" },
  itemName: { color: Colors.text, ...Font.cardTitle, textAlign: "right" },
  itemMeta: { color: Colors.textSecondary, ...Font.tiny, marginTop: Spacing.xs },
  itemDiscount: { color: Colors.danger, ...Font.tiny, marginTop: Spacing.xs },
  editBtn: { paddingHorizontal: Spacing.md, paddingVertical: Spacing.sm, borderRadius: Radius.sm, backgroundColor: Colors.surfaceAlt, borderWidth: 1, borderColor: Colors.border },
  editBtnText: { color: Colors.primary, ...Font.chip },

  /* Save button */
  saveBtn: { height: 48, backgroundColor: Colors.primary, borderRadius: Radius.sm, alignItems: "center", justifyContent: "center", marginTop: Spacing.md },
  saveBtnText: { color: Colors.textInverse, ...Font.button },
});
