import { Alert, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import { useEffect, useState } from "react";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ScreenContainer } from "@/components/screen-container";
import { apiCall } from "@/lib/_core/api";
import { useAuth } from "@/hooks/use-auth";

const labels = { YER: "YE", SAR: "SAR", USD: "USD" } as const;

export default function SettingsScreen() {
  const { user } = useAuth();
  const [currency, setCurrency] = useState<keyof typeof labels>("YER");

  useEffect(() => {
    apiCall<{ currency: keyof typeof labels }>("/api/preferences").then((data) => setCurrency(data.currency)).catch(() => undefined);
  }, []);

  const switchCurrency = async () => {
    const next = currency === "YER" ? "SAR" : currency === "SAR" ? "USD" : "YER";
    try {
      await apiCall("/api/preferences", { method: "PATCH", body: JSON.stringify({ currency: next }) });
      setCurrency(next);
    } catch {
      Alert.alert("تعذر حفظ العملة", "سجّلي الدخول ثم حاولي مجددًا.");
    }
  };

  const soon = (title: string) => Alert.alert(title, "سيتم ربط هذا الخيار بخدمة المنصة في النسخة التالية.");

  return (
    <ScreenContainer edges={["top", "bottom", "left", "right"]} className="bg-[#F6F6F6]">
      <View style={styles.header}><TouchableOpacity onPress={() => router.back()}><MaterialIcons name="arrow-forward" size={25} color="#171717" /></TouchableOpacity><Text style={styles.title}>إعدادات</Text><View style={{ width: 25 }} /></View>
      <ScrollView showsVerticalScrollIndicator={false}>
        <Section>
          <Row label="تسجيل الدخول / تسجيل" icon="person-outline" onPress={() => router.push("/login" as never)} />
          <Row label="دفتر العناوين" icon="location-on" onPress={() => router.push("/addresses" as never)} />
          <Row label="خيارات الدفع" icon="payment" onPress={() => soon("خيارات الدفع")} />
        </Section>
        <Section>
          <Row label="موقع" value={user?.governorate || "اليمن"} icon="public" onPress={() => soon("الموقع")} />
          <Row label="اللغة" value="العربية" icon="language" onPress={() => Alert.alert("اللغة", "واجهة المتجر عربية باتجاه RTL.")} />
          <Row label="عملة" value={labels[currency]} icon="attach-money" onPress={switchCurrency} />
        </Section>
        <Section>
          <Row label="جهات الاتصال المفضلة" icon="star-border" onPress={() => soon("جهات الاتصال المفضلة")} />
          <Row label="قائمة الاتصال المحظورة" icon="block" onPress={() => soon("قائمة الاتصال المحظورة")} />
          <Row label="إمكانية الوصول" icon="accessibility" onPress={() => soon("إمكانية الوصول")} />
          <Row label="مسح ذاكرة التخزين المؤقت" value="0 MB" icon="delete-sweep" onPress={() => Alert.alert("تم المسح", "تم مسح ذاكرة التخزين المؤقت المحلية.")} />
        </Section>
        <Section>
          <Row label="سياسة الخصوصية وملفات تعريف الارتباط" icon="privacy-tip" onPress={() => soon("سياسة الخصوصية")} />
          <Row label="الشروط والأحكام" icon="gavel" onPress={() => soon("الشروط والأحكام")} />
          <Row label="التقييم والملاحظات" icon="rate-review" onPress={() => soon("التقييم والملاحظات")} />
          <Row label="التواصل معنا" icon="support-agent" onPress={() => router.push("/support" as never)} />
        </Section>
        {user?.role === "admin" ? <Section><Row label="لوحة الإدارة" icon="admin-panel-settings" onPress={() => router.push("/admin" as never)} /></Section> : null}
        <Text style={styles.version}>شبيك · إصدار 1.0.0</Text>
      </ScrollView>
    </ScreenContainer>
  );
}

function Section({ children }: { children: React.ReactNode }) { return <View style={styles.section}>{children}</View>; }
function Row({ label, value, icon, onPress }: { label: string; value?: string; icon: any; onPress: () => void }) {
  return <TouchableOpacity style={styles.row} onPress={onPress}><MaterialIcons name="chevron-left" size={23} color="#A1A1A1" /><View style={styles.copy}><Text style={styles.label}>{label}</Text>{value ? <Text style={styles.value}>{value}</Text> : null}</View><MaterialIcons name={icon} size={22} color="#252525" /></TouchableOpacity>;
}

const styles = StyleSheet.create({ header: { height: 58, backgroundColor: "#FFF", paddingHorizontal: 16, flexDirection: "row", alignItems: "center", justifyContent: "space-between", borderBottomWidth: 1, borderColor: "#E8E8E8" }, title: { fontSize: 18, fontWeight: "900", color: "#111" }, section: { backgroundColor: "#FFF", marginTop: 11 }, row: { minHeight: 62, paddingHorizontal: 16, flexDirection: "row", alignItems: "center", gap: 12, borderBottomWidth: 1, borderColor: "#F0F0F0" }, copy: { flex: 1, alignItems: "flex-end" }, label: { fontSize: 15, color: "#222", textAlign: "right" }, value: { color: "#777", fontSize: 12, marginTop: 3, textAlign: "right" }, version: { textAlign: "center", color: "#999", fontSize: 10, marginVertical: 25 } });
