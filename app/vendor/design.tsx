import { useEffect, useState } from "react";
import { Alert, StyleSheet, Switch, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ScreenContainer } from "@/components/screen-container";
import { djangoApi } from "@/lib/django-api";

type Theme = { id: number; name: string; tokens: Record<string, string>; layout: Record<string, unknown>; is_active: boolean };

export default function VendorDesignScreen() {
  const [theme, setTheme] = useState<Theme | null>(null);
  const [name, setName] = useState("");
  const [primary, setPrimary] = useState("#E60023");
  const [showHero, setShowHero] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    djangoApi<{ results?: Theme[] }>("/api/themes/").then((data) => {
      const own = data.results?.find((item) => item.tokens?.owner === "vendor") ?? data.results?.[0];
      if (own) { setTheme(own); setName(own.name); setPrimary(own.tokens?.primary || "#E60023"); setShowHero(own.layout?.showHero !== false); }
    }).catch(() => undefined);
  }, []);

  async function save() {
    setSaving(true);
    try {
      const payload = { name: name || "هوية متجري", is_active: true, tokens: { primary, owner: "vendor" }, layout: { showHero }, sections: [] };
      const result = theme ? await djangoApi<Theme>(`/api/themes/${theme.id}/`, { method: "PATCH", body: JSON.stringify(payload) }) : await djangoApi<Theme>("/api/themes/", { method: "POST", body: JSON.stringify(payload) });
      setTheme(result); Alert.alert("تم الحفظ", "تم تحديث تصميم متجرك.");
    } catch (error) { Alert.alert("تعذر الحفظ", error instanceof Error ? error.message : "حدث خطأ"); }
    finally { setSaving(false); }
  }

  return <ScreenContainer className="bg-[#F5F5F5]" edges={["top", "bottom", "left", "right"]}>
    <View style={styles.header}><TouchableOpacity onPress={() => router.back()}><MaterialIcons name="arrow-forward" size={25} /></TouchableOpacity><Text style={styles.title}>تصميم متجري</Text><View style={{ width: 25 }} /></View>
    <View style={styles.card}>
      <Text style={styles.heading}>هوية المتجر</Text>
      <Text style={styles.label}>اسم السمة</Text><TextInput value={name} onChangeText={setName} placeholder="هوية الصيف" style={styles.input} textAlign="right" />
      <Text style={styles.label}>اللون الرئيسي</Text><View style={styles.colorRow}><View style={[styles.swatch, { backgroundColor: primary }]} /><TextInput value={primary} onChangeText={setPrimary} style={[styles.input, { flex: 1, marginBottom: 0 }]} textAlign="left" autoCapitalize="characters" /></View>
      <View style={styles.switchRow}><Text style={styles.label}>إظهار العرض الرئيسي</Text><Switch value={showHero} onValueChange={setShowHero} trackColor={{ true: "#E60023" }} /></View>
      <Text style={styles.note}>يستطيع التاجر تخصيص متجره ضمن الهوية العامة التي يحددها المدير. الألوان والحدود الأساسية يمكن تقييدها من إعدادات الإدارة.</Text>
      <TouchableOpacity style={styles.button} onPress={save} disabled={saving}><Text style={styles.buttonText}>{saving ? "جارٍ الحفظ..." : "حفظ التصميم"}</Text></TouchableOpacity>
    </View>
  </ScreenContainer>;
}

const styles = StyleSheet.create({ header: { padding: 16, backgroundColor: "#FFF", flexDirection: "row", justifyContent: "space-between", alignItems: "center" }, title: { fontSize: 20, fontWeight: "900" }, card: { backgroundColor: "#FFF", margin: 12, borderRadius: 10, padding: 16 }, heading: { fontSize: 19, fontWeight: "900", textAlign: "right", marginBottom: 18 }, label: { fontSize: 13, fontWeight: "700", textAlign: "right", marginBottom: 8 }, input: { backgroundColor: "#F7F7F7", borderWidth: 1, borderColor: "#E5E5E5", borderRadius: 7, padding: 12, marginBottom: 16 }, colorRow: { flexDirection: "row", alignItems: "center", gap: 9, marginBottom: 16 }, swatch: { width: 42, height: 42, borderRadius: 8 }, switchRow: { flexDirection: "row-reverse", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }, note: { color: "#777", fontSize: 12, lineHeight: 20, textAlign: "right", marginBottom: 20 }, button: { backgroundColor: "#111", padding: 15, borderRadius: 8, alignItems: "center" }, buttonText: { color: "#FFF", fontWeight: "900", fontSize: 16 } });
