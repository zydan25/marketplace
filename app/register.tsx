import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useState } from "react";
import { ScreenContainer } from "@/components/screen-container";
import { djangoRegister } from "@/lib/django-api";

const governorates = ["أمانة العاصمة", "عدن", "أبين", "البيضاء", "الضالع", "الحديدة", "الجوف", "المهرة", "المحويت", "عمران", "ذمار", "حضرموت", "حجة", "إب", "لحج", "مأرب", "ريمة", "صعدة", "صنعاء", "شبوة", "سقطرى", "تعز"];

type Form = { fullName: string; phone: string; password: string; governorate: string };

export default function RegisterScreen() {
  const { ref } = useLocalSearchParams<{ ref?: string }>();
  const [value, setValue] = useState<Form>({ fullName: "", phone: "", password: "", governorate: "" });
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const update = (key: keyof Form) => (next: string) => {
    setValue((current) => ({ ...current, [key]: next }));
    if (error) setError("");
  };

  const submit = async () => {
    const parts = value.fullName.trim().split(/\s+/).filter(Boolean);
    if (parts.length < 2) return setError("اكتب اسمك الكامل، على الأقل اسمين.");
    if (!value.phone.trim() || value.phone.trim().length < 9) return setError("أدخل رقم جوال صحيح.");
    if (!value.password || value.password.length < 8) return setError("كلمة المرور يجب أن تحتوي على 8 أحرف على الأقل.");
    if (!value.governorate) return setError("اختر المحافظة.");

    try {
      setLoading(true);
      const result = await djangoRegister({
        first_name: parts[0] || "",
        middle_name: parts[1] || "",
        third_name: parts[2] || "",
        last_name: parts.slice(3).join(" ") || "",
        phone: value.phone.trim(),
        password: value.password,
        governorate: value.governorate,
        referral_code: ref,
      });
      router.replace(result.user.role === "vendor" ? "/vendor" as never : "/profile" as never);
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر إنشاء الحساب.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScreenContainer edges={["top", "bottom"]} className="bg-[#FFF]">
      <View style={s.header}>
        <View style={{ width: 36 }} />
        <Text style={s.headerTitle}>إنشاء حساب جديد</Text>
        <TouchableOpacity style={s.back} onPress={() => router.back()}>
          <MaterialIcons name="close" size={21} color="#111" />
        </TouchableOpacity>
      </View>
      <ScrollView showsVerticalScrollIndicator={false} automaticallyAdjustKeyboardInsets keyboardShouldPersistTaps="handled" contentContainerStyle={s.content}>
        <Text style={s.sub}>أنشئ حسابك في شبيك واستفد من العروض والطلبات المحفوظة.</Text>
        {error ? <View style={s.errorBox}><MaterialIcons name="error-outline" size={19} color="#E60023" /><Text style={s.errorText}>{error}</Text></View> : null}
        <Field label="الاسم الكامل" icon="person-outline" value={value.fullName} onChangeText={update("fullName")} placeholder="مثال: أحمد محمد" />
        <Field label="رقم الجوال" icon="phone-android" value={value.phone} onChangeText={update("phone")} placeholder="77X XXX XXX" keyboardType="phone-pad" />
        <Field label="كلمة المرور" icon="lock-outline" value={value.password} onChangeText={update("password")} placeholder="8 أحرف على الأقل" secureTextEntry />
        <Text style={s.label}>المحافظة</Text>
        <TouchableOpacity style={[s.field, s.selectField]} onPress={() => setOpen((current) => !current)}>
          <Text style={[s.selectText, !value.governorate && s.placeholder]}>{value.governorate || "اختر المحافظة"}</Text>
          <MaterialIcons name={open ? "keyboard-arrow-up" : "keyboard-arrow-down"} size={20} color="#777" />
          <MaterialIcons name="location-on" size={19} color="#777" />
        </TouchableOpacity>
        {open ? <View style={s.govs}>{governorates.map((item) => <TouchableOpacity key={item} onPress={() => { update("governorate")(item); setOpen(false); }} style={[s.gov, value.governorate === item && s.govActive]}><Text style={[s.govText, value.governorate === item && s.govTextActive]}>{item}</Text></TouchableOpacity>)}</View> : null}
        <TouchableOpacity disabled={loading} style={[s.primary, loading && s.disabled]} onPress={submit}><Text style={s.primaryText}>{loading ? "جارٍ إنشاء الحساب..." : "إنشاء الحساب"}</Text></TouchableOpacity>
        <View style={s.switchRow}><Text style={s.switchText}>لديك حساب بالفعل؟</Text><TouchableOpacity onPress={() => router.replace("/login" as never)}><Text style={s.switchLink}>تسجيل الدخول</Text></TouchableOpacity></View>
        <Text style={s.terms}>بإنشاء الحساب، أنت توافق على شروط الاستخدام وسياسة الخصوصية.</Text>
      </ScrollView>
    </ScreenContainer>
  );
}

function Field({ label, icon, ...props }: { label: string; icon: string; value: string; onChangeText: (value: string) => void; placeholder: string; secureTextEntry?: boolean; keyboardType?: "phone-pad" }) {
  return <View style={s.formGroup}><Text style={s.label}>{label}</Text><View style={s.field}><TextInput {...props} style={s.input} textAlign="right" placeholderTextColor="#999" autoCapitalize="none" /><MaterialIcons name={icon as any} size={20} color="#777" /></View></View>;
}

const s = StyleSheet.create({
  header: { height: 54, paddingHorizontal: 18, flexDirection: "row", justifyContent: "space-between", alignItems: "center", borderBottomWidth: 1, borderColor: "#F5F5F5" },
  headerTitle: { fontSize: 16, fontWeight: "900", color: "#111" },
  back: { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F5F5F5", alignItems: "center", justifyContent: "center" },
  content: { paddingHorizontal: 22, paddingTop: 30, paddingBottom: 70, maxWidth: 440, width: "100%", alignSelf: "center" },
  sub: { color: "#777", fontSize: 12, textAlign: "center", marginBottom: 20, lineHeight: 20 },
  errorBox: { flexDirection: "row-reverse", backgroundColor: "#FFF0F0", padding: 11, borderRadius: 10, alignItems: "center", gap: 8, marginBottom: 16, borderWidth: 1, borderColor: "#FFD6D6" },
  errorText: { color: "#E60023", fontSize: 11, fontWeight: "700", flex: 1, textAlign: "right" },
  formGroup: { marginBottom: 13 },
  label: { fontSize: 12, fontWeight: "800", color: "#111", textAlign: "right", marginBottom: 7 },
  field: { height: 49, borderRadius: 12, backgroundColor: "#F9F9F9", borderWidth: 1, borderColor: "#ECECEC", flexDirection: "row", alignItems: "center", paddingHorizontal: 14 },
  input: { flex: 1, fontSize: 14, writingDirection: "rtl", color: "#111", marginRight: 9 },
  selectField: { justifyContent: "space-between" },
  selectText: { flex: 1, textAlign: "right", fontSize: 13, color: "#111", marginRight: 9 },
  placeholder: { color: "#999" },
  govs: { flexDirection: "row-reverse", flexWrap: "wrap", gap: 7, padding: 10, backgroundColor: "#F8F8F8", borderRadius: 12, borderWidth: 1, borderColor: "#ECECEC", marginBottom: 13 },
  gov: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 18, backgroundColor: "#FFF", borderWidth: 1, borderColor: "#DDD" },
  govActive: { backgroundColor: "#111", borderColor: "#111" },
  govText: { fontSize: 11, color: "#555" },
  govTextActive: { color: "#FFF", fontWeight: "700" },
  primary: { height: 50, borderRadius: 13, backgroundColor: "#111", alignItems: "center", justifyContent: "center", marginTop: 8 },
  disabled: { opacity: 0.6 },
  primaryText: { color: "#FFF", fontSize: 14, fontWeight: "800" },
  switchRow: { flexDirection: "row-reverse", justifyContent: "center", gap: 6, marginTop: 22 },
  switchText: { fontSize: 12, color: "#777" },
  switchLink: { fontSize: 12, fontWeight: "800", color: "#E60023" },
  terms: { color: "#999", fontSize: 10, textAlign: "center", marginTop: 26, lineHeight: 17 },
});
