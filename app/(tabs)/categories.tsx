import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ActivityIndicator, Alert, FlatList, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { useMemo, useState } from "react";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { ProductCard } from "@/components/product-card";
import { useProducts } from "@/hooks/use-products";
import { useServiceCatalog } from "@/hooks/use-service-catalog";
import { flattenServiceCategories, formatServiceMoney, submitServiceRequest, type Service, type ServiceItem } from "@/lib/service-catalog";

const providerNames: Record<string, string> = {
  "yemen-mobile": "يمن موبايل", sabafon: "سبأفون", you: "يو", why: "واي", "yemen-4g": "يمن فورجي",
  "yemen-net": "يمن نت", adenet: "عدن نت", electricity: "الكهرباء", water: "الماء", wholesale: "الخدمات الجماعية",
};

function providerName(service: Service) { return providerNames[service.categorySlug ?? ""] ?? service.categoryName ?? service.name; }
function serviceLabel(service: Service) {
  const text = `${service.code} ${service.name}`.toLowerCase();
  const provider = providerName(service);
  if (text.includes("denomination") || text.includes("فئات") || text.includes("شحن")) return `فئات ${provider}`;
  if (text.includes("offer") || text.includes("package") || text.includes("باقة") || text.includes("باقات")) return `باقات ${provider}`;
  if (text.includes("balance") || text.includes("رصيد")) return `رصيد ${provider}`;
  if (text.includes("bill") || text.includes("تسديد")) return `تسديد ${provider}`;
  if (text.includes("query") || text.includes("استعلام")) return `استعلام ${provider}`;
  if (text.includes("units") || text.includes("وحدات")) return `وحدات ${provider}`;
  return service.name;
}
function collectMainServices(main: any) { return flattenServiceCategories(main); }
function fieldValueType(type: string) { return type === "number" || type === "decimal" ? "numeric" : "default"; }

export default function CategoriesScreen() {
  const { products, loading: productsLoading, refresh: refreshProducts } = useProducts();
  const { catalog, loading: servicesLoading, error: servicesError, refresh: refreshServices } = useServiceCatalog();
  const insets = useSafeAreaInsets();
  const [selectedId, setSelectedId] = useState("all-products");
  const [search, setSearch] = useState("");
  const [gameFilter, setGameFilter] = useState("all");
  const [selectedItem, setSelectedItem] = useState<ServiceItem | null>(null);
  const [form, setForm] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const mains = catalog?.categories ?? [];
  const paymentServices = useMemo(() => mains.filter((main) => main.slug === "payments").flatMap(collectMainServices), [mains]);
  const gamesAndCardsServices = useMemo(() => mains.filter((main) => main.slug === "games" || main.slug === "digital").flatMap(collectMainServices), [mains]);
  const gameItems = useMemo(() => {
    const rows: Array<{ service: Service; item: ServiceItem }> = [];
    gamesAndCardsServices.forEach((service) => service.items.forEach((item) => {
      if (["game_products", "digital_products", "service_options"].includes(item.type)) rows.push({ service, item });
    }));
    const q = search.trim().toLowerCase();
    return rows.filter(({ service, item }) => (gameFilter === "all" || service.id === Number(gameFilter)) && (!q || `${service.name} ${service.code} ${item.name}`.toLowerCase().includes(q)));
  }, [gamesAndCardsServices, gameFilter, search]);

  const currentService = useMemo(() => {
    if (!selectedId.startsWith("service:")) return null;
    const id = Number(selectedId.slice(8));
    return [...paymentServices, ...gamesAndCardsServices].find((service) => service.id === id) ?? null;
  }, [gamesAndCardsServices, paymentServices, selectedId]);
  const currentItems = useMemo(() => {
    if (!currentService) return [];
    const q = search.trim().toLowerCase();
    return currentService.items.filter((item) => !q || `${item.name} ${currentService.name}`.toLowerCase().includes(q));
  }, [currentService, search]);
  const productCategories = useMemo(() => {
    const names = [...new Set(products.flatMap((product) => product.categories?.length ? product.categories : [product.category]).filter(Boolean))];
    return [{ id: "all-products", title: "منتجات المتجر" }, ...names.map((title) => ({ id: `product:${title}`, title }))];
  }, [products]);
  const productCategory = selectedId.startsWith("product:") ? selectedId.slice(8) : "";
  const visibleProducts = useMemo(() => productCategory ? products.filter((p) => (p.categories?.length ? p.categories : [p.category]).includes(productCategory)) : products, [productCategory, products]);
  const isGamesCards = selectedId === "games-cards";

  const selectService = (service: Service) => {
    setSelectedId(`service:${service.id}`);
    setSelectedItem(null);
    setSearch("");
    setForm(Object.fromEntries(service.fields.map((f) => [f.key, f.default == null ? "" : String(f.default)])));
  };
  const selectGameCardArea = () => { setSelectedId("games-cards"); setSelectedItem(null); setSearch(""); setGameFilter("all"); setForm({}); };
  const selectItem = (item: ServiceItem) => setSelectedItem(item);

  const submit = async () => {
    if (!currentService) return;
    for (const field of currentService.fields) {
      if (field.required && !String(form[field.key] ?? "").trim()) { Alert.alert("بيانات مطلوبة", `أدخل ${field.label}`); return; }
    }
    setSubmitting(true);
    try {
      const result = await submitServiceRequest({ serviceId: currentService.id, itemId: selectedItem?.id, itemType: selectedItem?.type, payload: form });
      Alert.alert("تم إرسال الطلب", `رقم العملية: ${result.id}\nالحالة: ${result.status}\nالمبلغ: ${formatServiceMoney(result.amount, result.currency)}`);
      setSelectedItem(null);
    } catch (error) { Alert.alert("تعذر تنفيذ الطلب", error instanceof Error ? error.message : "حدث خطأ غير متوقع."); }
    finally { setSubmitting(false); }
  };

  const refreshing = productsLoading || servicesLoading;
  return (
    <View style={[styles.page, { paddingTop: Math.max(insets.top, 8) }]}>
      <View style={styles.header}>
        <View style={styles.searchBox}><MaterialIcons name="search" size={20} color="#555" /><TextInput value={search} onChangeText={setSearch} placeholder={isGamesCards ? "ابحث باسم اللعبة أو البطاقة أو الفئة" : "ابحث عن باقة أو فئة أو منتج"} placeholderTextColor="#888" style={styles.searchInput} /></View>
        <Text style={styles.title}>الفئات</Text>
      </View>
      <View style={styles.content}>
        <View style={styles.side}>
          <FlatList
            data={paymentServices}
            keyExtractor={(item) => `service-${item.id}`}
            showsVerticalScrollIndicator={false}
            contentContainerStyle={styles.sideContent}
            ListHeaderComponent={<><Text style={styles.sideGroupTitle}>باقات وفئات الاتصالات</Text><TouchableOpacity onPress={() => { setSelectedId("all-products"); setSelectedItem(null); }} style={[styles.sideItem, selectedId === "all-products" && styles.sideItemActive]}><Text style={[styles.sideText, selectedId === "all-products" && styles.sideTextActive]}>منتجات المتجر</Text></TouchableOpacity></>}
            renderItem={({ item }) => <TouchableOpacity onPress={() => selectService(item)} style={[styles.sideItem, selectedId === `service:${item.id}` && styles.sideItemActive]}><MaterialIcons name={serviceLabel(item).includes("باقة") ? "local-offer" : serviceLabel(item).includes("فئة") ? "confirmation-number" : "phone-android"} size={18} color={selectedId === `service:${item.id}` ? "#171717" : "#777"} /><Text style={[styles.sideText, selectedId === `service:${item.id}` && styles.sideTextActive]} numberOfLines={3}>{serviceLabel(item)}</Text><Text style={styles.sideCount}>{item.items.length || ""}</Text></TouchableOpacity>}
            ListFooterComponent={<><Text style={styles.sideGroupTitle}>الألعاب والبطائق</Text><TouchableOpacity onPress={selectGameCardArea} style={[styles.sideItem, isGamesCards && styles.sideItemActive]}><MaterialIcons name="sports-esports" size={20} color={isGamesCards ? "#171717" : "#777"} /><Text style={[styles.sideText, isGamesCards && styles.sideTextActive]}>فئات الألعاب والبطائق</Text></TouchableOpacity><Text style={styles.sideGroupTitle}>فئات المنتجات</Text>{productCategories.slice(1).map((category) => <TouchableOpacity key={category.id} onPress={() => { setSelectedId(category.id); setSelectedItem(null); }} style={[styles.sideItem, selectedId === category.id && styles.sideItemActive]}><MaterialIcons name="category" size={17} color={selectedId === category.id ? "#171717" : "#777"} /><Text style={[styles.sideText, selectedId === category.id && styles.sideTextActive]} numberOfLines={2}>{category.title}</Text></TouchableOpacity>)}</>}
          />
        </View>
        <View style={styles.main}>
          {servicesError && !catalog ? <View style={styles.empty}><MaterialIcons name="wifi-off" size={42} color="#999" /><Text style={styles.emptyTitle}>تعذر تحميل الباقات والخدمات</Text><Text style={styles.emptyText}>{servicesError}</Text><TouchableOpacity style={styles.retry} onPress={refreshServices}><Text style={styles.retryText}>إعادة المحاولة</Text></TouchableOpacity></View>
          : selectedId === "all-products" || selectedId.startsWith("product:") ? <FlatList data={visibleProducts} keyExtractor={(item) => item.id} numColumns={2} showsVerticalScrollIndicator={false} columnWrapperStyle={visibleProducts.length > 1 ? styles.productRow : undefined} contentContainerStyle={[styles.products, { paddingBottom: 120 + insets.bottom }]} refreshing={refreshing} onRefresh={() => { void Promise.all([refreshProducts(), refreshServices()]); }} renderItem={({ item }) => <ProductCard product={item} />} ListHeaderComponent={<View style={styles.hero}><Text style={styles.heroTitle}>{productCategory || "منتجات المتجر"}</Text><Text style={styles.heroSub}>المنتجات العادية بالإضافة إلى خدمات الاتصالات والألعاب والبطائق.</Text></View>} ListEmptyComponent={<EmptyProducts loading={productsLoading} />} />
          : isGamesCards ? <FlatList data={gameItems} keyExtractor={({ service, item }) => `${service.id}-${item.type}-${item.id}`} showsVerticalScrollIndicator={false} contentContainerStyle={[styles.products, { paddingBottom: 120 + insets.bottom }]} refreshing={servicesLoading} onRefresh={refreshServices} ListHeaderComponent={<View><View style={styles.hero}><Text style={styles.heroTitle}>فئات الألعاب والبطائق</Text><Text style={styles.heroSub}>الألعاب والبطائق والمنتجات الرقمية في خانة واحدة، مع البحث والفرز حسب اللعبة.</Text></View><View style={styles.filterBox}><Text style={styles.filterLabel}>فرز حسب اللعبة</Text><View style={styles.filterList}>{["all", ...gamesAndCardsServices.map((s) => String(s.id))].map((id) => <TouchableOpacity key={id} onPress={() => setGameFilter(id)} style={[styles.filterChip, gameFilter === id && styles.filterChipActive]}><Text style={[styles.filterChipText, gameFilter === id && styles.filterChipTextActive]}>{id === "all" ? "كل الألعاب" : gamesAndCardsServices.find((s) => String(s.id) === id)?.name}</Text></TouchableOpacity>)}</View></View></View>} renderItem={({ service, item }) => <ServiceItemCard service={service} item={item} selected={false} onSelect={() => { selectService(service); selectItem(item); }} />} ListEmptyComponent={<View style={styles.empty}><MaterialIcons name="sports-esports" size={46} color="#999" /><Text style={styles.emptyTitle}>لا توجد فئات مطابقة</Text><Text style={styles.emptyText}>جرّب اسم لعبة آخر أو ألغِ الفرز الحالي.</Text></View>} />
          : currentService ? <FlatList data={currentItems} keyExtractor={(item) => `${item.type}-${item.id}`} showsVerticalScrollIndicator={false} contentContainerStyle={[styles.products, { paddingBottom: 120 + insets.bottom }]} refreshing={servicesLoading} onRefresh={refreshServices} ListHeaderComponent={<ServiceHeader service={currentService} selectedItem={selectedItem} form={form} setForm={setForm} submitting={submitting} onSubmit={submit} />} renderItem={({ item }) => <ServiceItemCard service={currentService} item={item} selected={selectedItem?.id === item.id && selectedItem?.type === item.type} onSelect={() => selectItem(item)} />} ListEmptyComponent={<View style={styles.empty}><MaterialIcons name="inventory-2" size={46} color="#999" /><Text style={styles.emptyTitle}>لا توجد باقات أو فئات حاليًا</Text><Text style={styles.emptyText}>أضف العناصر من لوحة إدارة الخدمات ثم حدّث هذه الصفحة.</Text></View>} />
          : <View style={styles.empty}><ActivityIndicator /><Text style={styles.emptyTitle}>جارٍ تحميل الخدمات...</Text></View>}
        </View>
      </View>
    </View>
  );
}

function ServiceHeader({ service, selectedItem, form, setForm, submitting, onSubmit }: { service: Service; selectedItem: ServiceItem | null; form: Record<string, string>; setForm: (value: Record<string, string>) => void; submitting: boolean; onSubmit: () => void }) {
  const hasFields = service.fields.length > 0 || service.pricing_mode === "amount";
  const fields = service.pricing_mode === "amount" ? [{ key: "amount", label: "المبلغ", type: "decimal", required: true, secret: false, choices: [], default: form.amount ?? "", validation: {} }, ...service.fields] : service.fields;
  return <View><View style={styles.hero}><Text style={styles.heroTitle}>{serviceLabel(service)}</Text><Text style={styles.heroSub}>{service.description || "اختر الباقة أو الفئة، ثم أدخل البيانات المطلوبة لإتمام الطلب."}</Text></View>{service.items.length ? <Text style={styles.sectionTitle}>{selectedItem ? `الفئة المختارة: ${selectedItem.name}` : "اختر باقة أو فئة"}</Text> : null}{hasFields ? <View style={styles.formCard}>{fields.map((field) => <ServiceFieldInput key={field.key} field={field as any} form={form} setForm={setForm} />)}<TouchableOpacity disabled={submitting || (service.items.length > 0 && !selectedItem)} onPress={onSubmit} style={[styles.submit, (submitting || (service.items.length > 0 && !selectedItem)) && styles.submitDisabled]}>{submitting ? <ActivityIndicator color="#FFF" /> : <Text style={styles.submitText}>{selectedItem ? "تنفيذ الطلب" : "تنفيذ الخدمة"}</Text>}</TouchableOpacity></View> : <View style={styles.note}><Text style={styles.noteText}>هذه الخدمة تُنفذ مباشرة بدون فئة محددة.</Text><TouchableOpacity disabled={submitting} onPress={onSubmit} style={styles.submit}><Text style={styles.submitText}>تنفيذ الخدمة</Text></TouchableOpacity></View>}</View>;
}

function ServiceFieldInput({ field, form, setForm }: { field: { key: string; label: string; type: string; required: boolean; secret: boolean; choices: string[] }; form: Record<string, string>; setForm: (value: Record<string, string>) => void }) {
  if (field.choices?.length) return <View style={styles.field}><Text style={styles.fieldLabel}>{field.label}{field.required ? " *" : ""}</Text><View style={styles.choiceRow}>{field.choices.map((choice) => <TouchableOpacity key={choice} onPress={() => setForm({ ...form, [field.key]: choice })} style={[styles.choice, form[field.key] === choice && styles.choiceActive]}><Text style={[styles.choiceText, form[field.key] === choice && styles.choiceTextActive]}>{choice}</Text></TouchableOpacity>)}</View></View>;
  return <View style={styles.field}><Text style={styles.fieldLabel}>{field.label}{field.required ? " *" : ""}</Text><TextInput value={form[field.key] ?? ""} onChangeText={(value) => setForm({ ...form, [field.key]: value })} placeholder={field.label} placeholderTextColor="#999" keyboardType={fieldValueType(field.type) === "numeric" ? "decimal-pad" : field.type === "email" ? "email-address" : "default"} secureTextEntry={field.secret} style={styles.input} /></View>;
}

function ServiceItemCard({ service, item, selected, onSelect }: { service: Service; item: ServiceItem; selected?: boolean; onSelect: () => void }) {
  const kindLabel = item.type === "game_products" ? "لعبة" : item.type === "digital_products" ? "بطاقة / برنامج" : item.type === "telecom_plans" ? "باقة" : item.type === "telecom_denominations" ? "فئة" : "خدمة";
  const icon = item.type === "game_products" ? "sports-esports" : item.type === "digital_products" ? "apps" : item.type === "telecom_plans" ? "local-offer" : item.type === "telecom_denominations" ? "confirmation-number" : "apps";
  return <TouchableOpacity onPress={onSelect} activeOpacity={0.86} style={[styles.serviceCard, selected && styles.serviceCardSelected, !item.availability?.available && styles.serviceCardDisabled]}><View style={styles.serviceIcon}><MaterialIcons name={icon as any} size={22} color="#333" /></View><View style={styles.serviceBody}><Text style={styles.serviceName}>{item.name}</Text><Text style={styles.serviceMeta}>{serviceLabel(service)} · {kindLabel}</Text>{item.metadata?.quota ? <Text style={styles.serviceMeta}>الحجم: {String(item.metadata.quota)} {String(item.metadata.quota_unit ?? "")}</Text> : null}{item.metadata?.validity_days ? <Text style={styles.serviceMeta}>الصلاحية: {String(item.metadata.validity_days)} يوم</Text> : null}</View><View style={styles.servicePrice}><Text style={styles.price}>{item.price ? formatServiceMoney(item.price, item.currency) : "—"}</Text><Text style={styles.selectText}>{item.availability?.available ? "اختيار" : item.availability?.reason ?? "غير متاح"}</Text></View></TouchableOpacity>;
}
function EmptyProducts({ loading }: { loading: boolean }) { return <View style={styles.empty}><MaterialIcons name="category" size={40} color="#999" /><Text style={styles.emptyTitle}>{loading ? "جارٍ تحميل المنتجات" : "لا توجد منتجات في هذه الفئة الآن"}</Text></View>; }

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: "#FFF" }, header: { paddingHorizontal: 12, paddingBottom: 9, borderBottomWidth: 1, borderColor: "#EEE", flexDirection: "row-reverse", alignItems: "center", gap: 8 }, title: { fontSize: 18, color: "#171717", fontWeight: "900" }, searchBox: { flex: 1, height: 42, borderRadius: 10, backgroundColor: "#F5F5F5", flexDirection: "row-reverse", alignItems: "center", paddingHorizontal: 10, gap: 7 }, searchInput: { flex: 1, fontSize: 12, color: "#171717", textAlign: "right" }, content: { flex: 1, flexDirection: "row-reverse" }, side: { width: 112, backgroundColor: "#F7F7F7" }, sideContent: { paddingBottom: 120 }, sideGroupTitle: { color: "#888", fontSize: 9, fontWeight: "900", paddingHorizontal: 7, paddingTop: 13, paddingBottom: 5, textAlign: "right" }, sideItem: { minHeight: 58, justifyContent: "center", alignItems: "center", paddingHorizontal: 6, borderRightWidth: 3, borderRightColor: "transparent", gap: 3 }, sideItemActive: { backgroundColor: "#FFF", borderRightColor: "#171717" }, sideText: { color: "#747474", textAlign: "center", fontSize: 10, lineHeight: 14 }, sideTextActive: { color: "#171717", fontWeight: "900" }, sideCount: { color: "#999", fontSize: 8 }, main: { flex: 1, minWidth: 0 }, products: { paddingHorizontal: 10, paddingTop: 10 }, productRow: { gap: 9 }, hero: { minHeight: 88, marginBottom: 12, borderRadius: 13, backgroundColor: "#F1F1F1", justifyContent: "center", alignItems: "flex-end", padding: 14 }, heroTitle: { color: "#171717", fontWeight: "900", fontSize: 18, textAlign: "right" }, heroSub: { color: "#777", fontSize: 10, marginTop: 4, textAlign: "right", lineHeight: 16 }, filterBox: { marginBottom: 9, padding: 9, borderRadius: 12, backgroundColor: "#FAFAFA", borderWidth: 1, borderColor: "#ECECEC" }, filterLabel: { fontSize: 10, fontWeight: "900", color: "#555", textAlign: "right", marginBottom: 7 }, filterList: { flexDirection: "row-reverse", flexWrap: "wrap", gap: 6 }, filterChip: { paddingVertical: 7, paddingHorizontal: 10, backgroundColor: "#EFEFEF", borderRadius: 999 }, filterChipActive: { backgroundColor: "#171717" }, filterChipText: { fontSize: 9, color: "#666", fontWeight: "800" }, filterChipTextActive: { color: "#FFF" }, sectionTitle: { fontSize: 12, fontWeight: "900", color: "#222", marginBottom: 8, textAlign: "right" }, serviceCard: { backgroundColor: "#FFF", borderWidth: 1, borderColor: "#E8E8E8", borderRadius: 13, marginBottom: 9, padding: 10, flexDirection: "row-reverse", alignItems: "center", gap: 9 }, serviceCardSelected: { borderColor: "#222", backgroundColor: "#FAFAFA" }, serviceCardDisabled: { opacity: 0.55 }, serviceIcon: { width: 44, height: 44, borderRadius: 12, backgroundColor: "#EFEFEF", alignItems: "center", justifyContent: "center" }, serviceBody: { flex: 1, minWidth: 0, alignItems: "flex-end" }, serviceName: { fontSize: 13, color: "#171717", fontWeight: "900", textAlign: "right" }, serviceMeta: { fontSize: 9, color: "#777", marginTop: 2, textAlign: "right" }, servicePrice: { alignItems: "flex-start", minWidth: 64 }, price: { fontSize: 11, color: "#171717", fontWeight: "900" }, selectText: { fontSize: 9, color: "#777", marginTop: 4 }, formCard: { padding: 11, backgroundColor: "#FAFAFA", borderWidth: 1, borderColor: "#EAEAEA", borderRadius: 13, marginBottom: 12 }, field: { marginBottom: 9 }, fieldLabel: { fontSize: 10, color: "#555", fontWeight: "900", textAlign: "right", marginBottom: 5 }, input: { height: 42, borderWidth: 1, borderColor: "#D9D9D9", borderRadius: 10, backgroundColor: "#FFF", color: "#171717", paddingHorizontal: 10, textAlign: "right", fontSize: 12 }, choiceRow: { flexDirection: "row-reverse", flexWrap: "wrap", gap: 6 }, choice: { paddingVertical: 7, paddingHorizontal: 10, backgroundColor: "#FFF", borderRadius: 9, borderWidth: 1, borderColor: "#DDD" }, choiceActive: { backgroundColor: "#171717", borderColor: "#171717" }, choiceText: { color: "#666", fontSize: 9 }, choiceTextActive: { color: "#FFF", fontWeight: "800" }, submit: { minHeight: 42, borderRadius: 10, backgroundColor: "#171717", alignItems: "center", justifyContent: "center", marginTop: 3, paddingHorizontal: 14 }, submitDisabled: { opacity: 0.45 }, submitText: { color: "#FFF", fontSize: 11, fontWeight: "900" }, note: { padding: 12, backgroundColor: "#F7F7F7", borderRadius: 12, marginBottom: 12 }, noteText: { color: "#777", fontSize: 10, textAlign: "right", marginBottom: 8 }, empty: { alignItems: "center", justifyContent: "center", padding: 30, minHeight: 260 }, emptyTitle: { color: "#333", fontSize: 15, fontWeight: "900", marginTop: 8, textAlign: "center" }, emptyText: { color: "#777", fontSize: 10, marginTop: 6, textAlign: "center", lineHeight: 16 }, retry: { marginTop: 12, backgroundColor: "#171717", borderRadius: 10, paddingHorizontal: 16, paddingVertical: 9 }, retryText: { color: "#FFF", fontSize: 10, fontWeight: "900" },
});
