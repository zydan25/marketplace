import { useState, useEffect } from "react";
import { Alert, ScrollView, StyleSheet, Switch, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ScreenContainer } from "@/components/screen-container";
import { djangoApi } from "@/lib/django-api";

type Theme = { id: number; name: string; tokens: Record<string, string>; layout: Record<string, unknown>; is_active: boolean };

export default function VendorDesignScreen() {
  const [theme, setTheme] = useState<Theme | null>(null);
  const [name, setName] = useState("");
  const [primary, setPrimary] = useState("#E60023");
  const [background, setBackground] = useState("#FFFFFF");
  const [showHero, setShowHero] = useState(true);
  const [showCategories, setShowCategories] = useState(true);
  const [showFlashSale, setShowFlashSale] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    djangoApi<{ results?: Theme[] }>("/api/themes/").then((data) => {
      const own = (data.results ?? []).find((item) => item.name || item.id);
      if (own) {
        setTheme(own);
        setName(own.name);
        setPrimary(own.tokens?.primary || "#E60023");
        setBackground(own.tokens?.background || "#FFFFFF");
        setShowHero(own.layout?.showHero !== false);
        setShowCategories(own.layout?.showCategories !== false);
        setShowFlashSale(own.layout?.showFlashSale !== false);
      }
    }).catch(() => undefined).finally(() => setLoading(false));
  }, []);

  async function save() {
    const validHex = (value: string) => /^#[0-9a-fA-F]{6}$/.test(value.trim());
    if (!validHex(primary) || !validHex(background)) return Alert.alert("لون غير صالح", "استخدم رمز HEX بالشكل #RRGGBB.");
    setSaving(true);
    try {
      const payload = {
        name: name.trim() || "هوية متجري",
        is_active: true,
        tokens: { primary: primary.trim().toUpperCase(), background: background.trim().toUpperCase(), owner: "vendor" },
        layout: { showHero, showCategories, showFlashSale, productGrid: 2, direction: "rtl" },
        sections: ["hero", "categories", "flash_sale", "products"],
      };
      const result = theme ? await djangoApi<Theme>(`/api/themes/${theme.id}/`, { method: "PATCH", body: JSON.stringify(payload) }) : await djangoApi<Theme>("/api/themes/", { method: "POST", body: JSON.stringify(payload) });
      setTheme(result);
      Alert.alert("تم الحفظ", "تم تحديث هوية وتصميم متجرك.");
    } catch (error) {
      Alert.alert("تعذر الحفظ", error instanceof Error ? error.message : "حدث خطأ");
    } finally { setSaving(false); }
  }

  if (loading) return <ScreenContainer><View style={styles.center}><Text style={styles.muted}>جارٍ تحميل إعدادات التصميم...</Text></View></ScreenContainer>;
  return <ScreenContainer className="bg-[#F8F9FA]" edges={["top", "bottom", "left", "right"]}>
    <View style={styles.header}><TouchableOpacity onPress={() => router.back()}><MaterialIcons name="arrow-forward" size={25} color="#111" /></TouchableOpacity><Text style={styles.title}>تخصيص المتجر</Text><View style={{ width: 25 }} /></View>
    <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      <View style={[styles.preview, { backgroundColor: primary }]}><View style={[styles.previewDot, { backgroundColor: background }]} /><View style={styles.previewCopy}><Text style={styles.previewName}>{name || "هوية متجري"}</Text><Text style={styles.previewText}>معاينة هوية وألوان المتجر</Text></View><MaterialIcons name="storefront" size={27} color="#FFF" /></View>
      <View style={styles.card}>
        <Text style={styles.heading}>هوية المتجر</Text>
        <Text style={styles.label}>اسم الهوية</Text><TextInput value={name} onChangeText={setName} placeholder="هوية متجري" style={styles.input} textAlign="right" />
        <Text style={styles.label}>اللون الرئيسي</Text><View style={styles.colorRow}><View style={[styles.swatch, { backgroundColor: validColor(primary) ? primary : "#DDD" }]} /><TextInput value={primary} onChangeText={setPrimary} style={[styles.input, { flex: 1, marginBottom: 0 }]} textAlign="left" autoCapitalize="characters" /></View>
        <Text style={styles.label}>لون خلفية المتجر</Text><View style={styles.colorRow}><View style={[styles.swatch, { backgroundColor: validColor(background) ? background : "#DDD" }]} /><TextInput value={background} onChangeText={setBackground} style={[styles.input, { flex: 1, marginBottom: 0 }]} textAlign="left" autoCapitalize="characters" /></View>
      </View>
      <View style={styles.card}>
        <Text style={styles.heading}>أقسام واجهة المتجر</Text>
        <Option label="العرض الرئيسي والبنرات" value={showHero} onChange={setShowHero} />
        <Option label="الأقسام والفئات الدائرية" value={showCategories} onChange={setShowCategories} />
        <Option label="شريط العروض السريعة" value={showFlashSale} onChange={setShowFlashSale} />
        <Text style={styles.note}>تتحكم هذه الخيارات في هوية العرض فقط، ولا تسمح بتجاوز سياسات المنصة أو صلاحيات الإدارة.</Text>
      </View>
      <TouchableOpacity style={styles.button} onPress={save} disabled={saving}><Text style={styles.buttonText}>{saving ? "جارٍ الحفظ..." : "حفظ ونشر التصميم"}</Text></TouchableOpacity>
    </ScrollView>
  </ScreenContainer>;
}
function validColor(value: string) { return /^#[0-9a-fA-F]{6}$/.test(value.trim()); }
function Option({ label, value, onChange }: { label: string; value: boolean; onChange: (value: boolean) => void }) {
  return <View style={styles.option}><Switch value={value} onValueChange={onChange} trackColor={{ true: "#E60023" }} /><Text style={styles.optionText}>{label}</Text></View>;
}
const styles = StyleSheet.create({ header: { height: 60, paddingHorizontal: 16, backgroundColor: "#FFF", flexDirection: "row", justifyContent: "space-between", alignItems: "center", borderBottomWidth: 1, borderColor: "#EEE" }, title: { fontSize: 19, fontWeight: "900", color: "#111" }, content: { padding: 12, paddingBottom: 60 }, preview: { borderRadius: 14, padding: 18, flexDirection: "row-reverse", alignItems: "center", gap: 12, marginBottom: 12 }, previewDot: { width: 32, height: 32, borderRadius: 16 }, previewCopy: { flex: 1, alignItems: "flex-end" }, previewName: { color: "#FFF", fontSize: 17, fontWeight: "900" }, previewText: { color: "#EEE", fontSize: 11, marginTop: 3 }, card: { backgroundColor: "#FFF", borderRadius: 12, padding: 16, marginBottom: 12 }, heading: { fontSize: 17, fontWeight: "900", textAlign: "right", marginBottom: 18, color: "#111" }, label: { fontSize: 12, fontWeight: "700", textAlign: "right", marginBottom: 8, color: "#444" }, input: { backgroundColor: "#F8F9FA", borderWidth: 1, borderColor: "#E5E5E5", borderRadius: 8, padding: 12, marginBottom: 15, color: "#111" }, colorRow: { flexDirection: "row", alignItems: "center", gap: 9, marginBottom: 15 }, swatch: { width: 42, height: 42, borderRadius: 8, borderWidth: 1, borderColor: "#DDD" }, option: { flexDirection: "row-reverse", justifyContent: "space-between", alignItems: "center", paddingVertical: 11, borderBottomWidth: 1, borderColor: "#F0F0F0" }, optionText: { fontSize: 14, fontWeight: "700", color: "#333" }, note: { color: "#777", fontSize: 11, lineHeight: 18, textAlign: "right", marginTop: 15 }, button: { backgroundColor: "#E60023", padding: 16, borderRadius: 9, alignItems: "center" }, buttonText: { color: "#FFF", fontWeight: "900", fontSize: 15 }, center:{flex:1,alignItems:"center",justifyContent:"center"}, muted:{color:"#777"} });
