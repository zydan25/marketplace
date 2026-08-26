import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import * as ImagePicker from "expo-image-picker";
import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Alert, Image, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { ScreenContainer } from "@/components/screen-container";
import { getService, submitService, type Service } from "@/lib/service-api";

export default function ServiceDetailScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const [service, setService] = useState<Service | null>(null);
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!slug) return;
    void (async () => {
      try { setService(await getService(String(slug))); }
      catch (error) { Alert.alert("تعذر تحميل الخدمة", error instanceof Error ? error.message : "حاول مرة أخرى"); }
      finally { setLoading(false); }
    })();
  }, [slug]);

  const orderedFields = useMemo(() => [...(service?.fields ?? [])].sort((a, b) => a.sort_order - b.sort_order), [service]);
  const setValue = (key: string, value: unknown) => setValues((current) => ({ ...current, [key]: value }));

  async function submit() {
    if (!service) return;
    for (const field of orderedFields) {
      const value = values[field.key];
      if (field.is_required && (value == null || value === "" || (Array.isArray(value) && value.length === 0))) {
        Alert.alert("بيانات ناقصة", `الحقل «${field.label}» مطلوب.`); return;
      }
    }
    setSaving(true);
    try {
      await submitService(service.id, values);
      Alert.alert("تم التقديم", "تم تسجيل طلب الخدمة بنجاح.", [{ text: "حسنًا", onPress: () => router.back() }]);
    } catch (error) { Alert.alert("تعذر تقديم الخدمة", error instanceof Error ? error.message : "حاول مرة أخرى."); }
    finally { setSaving(false); }
  }

  if (loading) return <ScreenContainer className="bg-white"><View style={styles.center}><ActivityIndicator /></View></ScreenContainer>;
  if (!service) return <ScreenContainer className="bg-white"><View style={styles.center}><Text>الخدمة غير موجودة</Text></View></ScreenContainer>;

  return <ScreenContainer className="bg-[#F7F7F7]"><ScrollView contentInsetAdjustmentBehavior="automatic" showsVerticalScrollIndicator={false} contentContainerStyle={styles.content}>
    <View style={styles.header}><Pressable onPress={() => router.back()}><MaterialIcons name="arrow-forward" size={24} color="#111" /></Pressable><Text style={styles.headerTitle}>تفاصيل الخدمة</Text><View style={{ width: 24 }} /></View>
    {service.banner_url ? <Image source={{ uri: service.banner_url }} style={styles.banner} /> : <View style={styles.bannerFallback}><Text style={styles.bannerTitle}>{service.name}</Text></View>}
    <View style={styles.card}><Text style={styles.title}>{service.name}</Text>{service.description ? <Text style={styles.description}>{service.description}</Text> : null}<Text style={styles.price}>{service.price} {service.currency}</Text></View>
    <View style={styles.form}>{orderedFields.map((field) => <DynamicField key={field.id} field={field} value={values[field.key]} onChange={(value) => setValue(field.key, value)} />)}</View>
    <Pressable onPress={submit} disabled={saving} style={[styles.submit, saving && styles.disabled]}><Text style={styles.submitText}>{saving ? "جارٍ التقديم..." : Number(service.price) > 0 ? "تقديم وشراء الخدمة" : "تقديم الطلب"}</Text></Pressable>
  </ScrollView></ScreenContainer>;
}

function DynamicField({ field, value, onChange }: { field: Service["fields"][number]; value: unknown; onChange: (value: unknown) => void }) {
  const common = { borderWidth: 1, borderColor: "#E4E4E4", backgroundColor: "#FFF", borderRadius: 12, paddingHorizontal: 12, fontSize: 13, textAlign: "right" as const };
  const label = <Text style={styles.label}>{field.label}{field.is_required ? " *" : ""}</Text>;
  const help = field.help_text ? <Text style={styles.help}>{field.help_text}</Text> : null;

  if (field.field_type === "textarea") return <View style={styles.field}>{label}<TextInput multiline value={String(value ?? "")} onChangeText={onChange} placeholder={field.placeholder} placeholderTextColor="#999" style={[common, { minHeight: 110, paddingTop: 12 }]} />{help}</View>;
  if (["number", "phone", "date"].includes(field.field_type)) return <View style={styles.field}>{label}<TextInput value={String(value ?? "")} onChangeText={onChange} placeholder={field.placeholder} placeholderTextColor="#999" keyboardType={field.field_type === "number" ? "numeric" : field.field_type === "phone" ? "phone-pad" : "default"} style={[common, { height: 46 }]} />{help}</View>;
  if (field.field_type === "checkbox") return <Pressable onPress={() => onChange(!Boolean(value))} style={styles.checkRow}><MaterialIcons name={Boolean(value) ? "check-box" : "check-box-outline-blank"} size={22} color={Boolean(value) ? "#111" : "#999"} /><Text style={styles.label}>{field.label}{field.is_required ? " *" : ""}</Text></Pressable>;
  if (field.field_type === "select") return <View style={styles.field}>{label}<View style={styles.options}>{(field.options ?? []).map((option, index) => { const item = normalizeOption(option, index); const active = String(value ?? "") === item.value; return <Pressable key={`${item.value}-${index}`} onPress={() => onChange(item.value)} style={[styles.option, active && styles.optionActive]}><Text style={[styles.optionText, active && styles.optionTextActive]}>{item.label}</Text></Pressable>; })}</View>{help}</View>;
  if (field.field_type === "multiselect") { const selected = Array.isArray(value) ? value.map(String) : []; return <View style={styles.field}>{label}<View style={styles.options}>{(field.options ?? []).map((option, index) => { const item = normalizeOption(option, index); const active = selected.includes(item.value); return <Pressable key={`${item.value}-${index}`} onPress={() => onChange(active ? selected.filter((v) => v !== item.value) : [...selected, item.value])} style={[styles.option, active && styles.optionActive]}><Text style={[styles.optionText, active && styles.optionTextActive]}>{item.label}</Text></Pressable>; })}</View>{help}</View>; }
  if (field.field_type === "image") return <ImageField label={field.label} value={value} onChange={onChange} help={field.help_text} required={field.is_required} />;
  return <View style={styles.field}>{label}<TextInput value={String(value ?? "")} onChangeText={onChange} placeholder={field.placeholder} placeholderTextColor="#999" style={[common, { height: 46 }]} />{help}</View>;
}

function normalizeOption(option: unknown, index: number) {
  if (option && typeof option === "object" && !Array.isArray(option)) {
    const row = option as Record<string, unknown>;
    return { value: String(row.value ?? row.id ?? index), label: String(row.label ?? row.name ?? row.value ?? index + 1) };
  }
  return { value: String(option ?? index), label: String(option ?? index + 1) };
}

function ImageField({ label, value, onChange, help, required }: { label: string; value: unknown; onChange: (value: unknown) => void; help: string; required: boolean }) {
  const image = typeof value === "string" ? value : "";
  async function pick() {
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], quality: 0.8, base64: true });
    if (result.canceled || !result.assets[0]?.base64) return;
    const asset = result.assets[0];
    onChange(`data:${asset.mimeType ?? "image/jpeg"};base64,${asset.base64}`);
  }
  return <View style={styles.field}><Text style={styles.label}>{label}{required ? " *" : ""}</Text><Pressable onPress={pick} style={styles.upload}><MaterialIcons name="add-photo-alternate" size={22} color="#777" />{image ? <Image source={{ uri: image }} style={styles.uploadImage} /> : <Text style={styles.uploadText}>رفع صورة</Text>}</Pressable>{help ? <Text style={styles.help}>{help}</Text> : null}</View>;
}

const styles = StyleSheet.create({ content: { paddingBottom: 120 }, header: { height: 58, paddingHorizontal: 14, flexDirection: "row-reverse", alignItems: "center", justifyContent: "space-between", backgroundColor: "#FFF" }, headerTitle: { fontSize: 17, fontWeight: "900", color: "#111" }, banner: { width: "100%", height: 210, backgroundColor: "#EEE" }, bannerFallback: { height: 180, backgroundColor: "#111", alignItems: "center", justifyContent: "center" }, bannerTitle: { color: "#FFF", fontSize: 24, fontWeight: "900" }, card: { margin: 12, padding: 16, borderRadius: 16, backgroundColor: "#FFF" }, title: { fontSize: 20, fontWeight: "900", textAlign: "right", color: "#111" }, description: { fontSize: 12, lineHeight: 20, color: "#666", textAlign: "right", marginTop: 8 }, price: { fontSize: 16, fontWeight: "900", textAlign: "right", marginTop: 12, color: "#111" }, form: { paddingHorizontal: 12, gap: 12 }, field: { gap: 6 }, label: { fontSize: 11, fontWeight: "900", color: "#222", textAlign: "right" }, help: { fontSize: 9, color: "#888", textAlign: "right" }, options: { flexDirection: "row-reverse", flexWrap: "wrap", gap: 8 }, option: { paddingHorizontal: 12, paddingVertical: 9, borderRadius: 20, borderWidth: 1, borderColor: "#DDD", backgroundColor: "#FFF" }, optionActive: { backgroundColor: "#111", borderColor: "#111" }, optionText: { fontSize: 11, color: "#555", fontWeight: "700" }, optionTextActive: { color: "#FFF" }, checkRow: { flexDirection: "row-reverse", alignItems: "center", gap: 8, paddingVertical: 6 }, upload: { height: 130, borderRadius: 14, backgroundColor: "#FFF", borderWidth: 1, borderColor: "#DDD", alignItems: "center", justifyContent: "center", overflow: "hidden", gap: 8 }, uploadImage: { width: "100%", height: "100%", position: "absolute" }, uploadText: { fontSize: 11, color: "#666", fontWeight: "700" }, submit: { margin: 14, height: 48, borderRadius: 24, backgroundColor: "#E60023", alignItems: "center", justifyContent: "center" }, submitText: { color: "#FFF", fontSize: 13, fontWeight: "900" }, disabled: { opacity: .5 }, center: { flex: 1, alignItems: "center", justifyContent: "center" } });