import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { Alert, Image, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useState } from "react";
import { ScreenContainer } from "@/components/screen-container";
import * as Api from "@/lib/_core/api";
import * as Auth from "@/lib/_core/auth";
const governorates = ["أمانة العاصمة", "عدن", "أبين", "البيضاء", "الضالع", "الحديدة", "الجوف", "المهرة", "المحويت", "عمران", "ذمار", "حضرموت", "حجة", "إب", "لحج", "مأرب", "ريمة", "صعدة", "صنعاء", "شبوة", "سقطرى", "تعز"];
export default function RegisterScreen() {
  const { ref } = useLocalSearchParams<{ ref?: string }>();
  const [v, setV] = useState({ fullName: "", phone: "", password: "", governorate: "" });
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const update = (key: keyof typeof v) => (value: string) => {
    setV((current) => ({ ...current, [key]: value }));
    if (error) setError("");
  };

  const submit = async () => {
    const nameParts = v.fullName.trim().split(" ").filter(Boolean);
    if (nameParts.length < 2) {
      return setError("يرجى كتابة الاسم الثنائي أو الرباعي كاملًا.");
    }
    if (!v.phone.trim() || v.phone.length < 9) {
      return setError("يرجى إدخال رقم جوال صحيح.");
    }
    if (!v.password || v.password.length < 6) {
      return setError("كلمة المرور يجب أن تكون 6 أحرف على الأقل.");
    }
    if (!v.governorate) {
      return setError("يرجى اختيار المحافظة من القائمة.");
    }

    try {
      setLoading(true);
      setError("");
      // Split the full name into the format expected by the API
      const payload = {
        firstName: nameParts[0],
        secondName: nameParts[1] || "",
        thirdName: nameParts[2] || "",
        familyName: nameParts.slice(3).join(" ") || "",
        phone: v.phone.trim(),
        password: v.password,
        governorate: v.governorate,
        referralCode: ref
      };
      const result = await Api.registerWithPhone(payload);
      await Auth.setSessionToken(result.sessionToken);
      await Auth.setUserInfo({ ...result.user, lastSignedIn: new Date(result.user.lastSignedIn) });
      router.replace("/profile" as never);
    } catch (err) {
      setError(err instanceof Error ? err.message : "رقم الجوال مستخدم مسبقًا أو حدث خطأ.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScreenContainer edges={["top"]} className="bg-[#FFF]">
      <View style={s.header}>
        <View style={{ width: 36 }} />
        <Text style={s.headerTitle}>إنشاء حساب جديد</Text>
        <TouchableOpacity style={s.back} onPress={() => router.back()}>
          <MaterialIcons name="close" size={22} color="#111" />
        </TouchableOpacity>
      </View>
      <ScrollView contentContainerStyle={s.content} automaticallyAdjustKeyboardInsets>
        <Text style={s.sub}>انضمي إلى شبيك لتتسوقي أحدث الموديلات وتستفيدي من العروض الحصرية.</Text>
        
        {error ? (
          <View style={s.errorBox}>
            <MaterialIcons name="error-outline" size={20} color="#E60023" />
            <Text style={s.errorText}>{error}</Text>
          </View>
        ) : null}

        <View style={s.formGroup}>
          <Text style={s.label}>الاسم الكامل</Text>
          <View style={s.field}>
            <TextInput value={v.fullName} onChangeText={update("fullName")} placeholder="مثال: فاطمة محمد أحمد" style={s.input} textAlign="right" placeholderTextColor="#999" />
            <MaterialIcons name="person-outline" size={20} color="#777" />
          </View>
        </View>

        <View style={s.formGroup}>
          <Text style={s.label}>رقم الجوال</Text>
          <View style={s.field}>
            <TextInput value={v.phone} onChangeText={update("phone")} placeholder="77X XXX XXX" style={s.input} textAlign="right" placeholderTextColor="#999" keyboardType="phone-pad" />
            <MaterialIcons name="phone-android" size={20} color="#777" />
          </View>
        </View>

        <View style={s.formGroup}>
          <Text style={s.label}>كلمة المرور</Text>
          <View style={s.field}>
            <TextInput value={v.password} onChangeText={update("password")} placeholder="6 أحرف على الأقل" style={s.input} textAlign="right" placeholderTextColor="#999" secureTextEntry />
            <MaterialIcons name="lock-outline" size={20} color="#777" />
          </View>
        </View>

        <View style={s.formGroup}>
          <Text style={s.label}>المحافظة</Text>
          <TouchableOpacity style={[s.field, s.selectField]} onPress={() => setOpen(!open)}>
            <MaterialIcons name={open ? "keyboard-arrow-up" : "keyboard-arrow-down"} size={20} color="#777" />
            <Text style={[s.selectText, !v.governorate && s.placeholder]}>{v.governorate || "اختر المحافظة"}</Text>
            <MaterialIcons name="location-on" size={20} color="#777" />
          </TouchableOpacity>
        </View>

        {open && (
          <View style={s.govs}>
            {governorates.map((item) => (
              <TouchableOpacity key={item} onPress={() => { update("governorate")(item); setOpen(false); }} style={[s.gov, v.governorate === item && s.govActive]}>
                <Text style={[s.govText, v.governorate === item && s.govTextActive]}>{item}</Text>
              </TouchableOpacity>
            ))}
          </View>
        )}

        <TouchableOpacity disabled={loading} style={[s.primary, loading && s.disabled]} onPress={submit}>
          <Text style={s.primaryText}>{loading ? "جارِ الإنشاء..." : "إنشاء الحساب"}</Text>
        </TouchableOpacity>
        
        <View style={s.switchRow}>
          <Text style={s.switchText}>لديك حساب بالفعل؟</Text>
          <TouchableOpacity onPress={() => router.replace("/login" as never)}>
            <Text style={s.switchLink}>تسجيل الدخول</Text>
          </TouchableOpacity>
        </View>
        
        <Text style={s.terms}>بإنشاء الحساب، أنت توافق على شروط الاستخدام وسياسة الخصوصية الخاصة بمنصة شبيك.</Text>
      </ScrollView>
    </ScreenContainer>
  );
}

const s = StyleSheet.create({
  header: { height: 54, paddingHorizontal: 20, flexDirection: "row", justifyContent: "space-between", alignItems: "center", borderBottomWidth: 1, borderColor: "#F5F5F5" },
  headerTitle: { fontSize: 16, fontWeight: "900", color: "#111" },
  back: { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F5F5F5", alignItems: "center", justifyContent: "center" },
  content: { paddingHorizontal: 24, paddingTop: 40, paddingBottom: 80, maxWidth: 450, width: "100%", alignSelf: "center" },
  sub: { color: "#777", fontSize: 13, textAlign: "center", marginBottom: 24, lineHeight: 22 },
  errorBox: { flexDirection: "row-reverse", backgroundColor: "#FFF0F0", padding: 12, borderRadius: 8, alignItems: "center", gap: 8, marginBottom: 20, borderWidth: 1, borderColor: "#FFD6D6" },
  errorText: { color: "#E60023", fontSize: 12, fontWeight: "700", flex: 1, textAlign: "right" },
  formGroup: { marginBottom: 16 },
  label: { fontSize: 13, fontWeight: "800", color: "#111", textAlign: "right", marginBottom: 8 },
  field: { height: 50, borderRadius: 12, backgroundColor: "#F9F9F9", borderWidth: 1, borderColor: "#EFEFEF", flexDirection: "row", alignItems: "center", paddingHorizontal: 16 },
  input: { flex: 1, fontSize: 14, writingDirection: "rtl", color: "#111", marginRight: 10 },
  selectField: { justifyContent: "space-between" },
  selectText: { flex: 1, textAlign: "right", fontSize: 14, color: "#111", marginRight: 10 },
  placeholder: { color: "#999" },
  govs: { flexDirection: "row-reverse", flexWrap: "wrap", gap: 8, padding: 12, backgroundColor: "#F9F9F9", borderRadius: 12, borderWidth: 1, borderColor: "#EFEFEF", marginBottom: 16 },
  gov: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20, backgroundColor: "#FFF", borderWidth: 1, borderColor: "#DDD" },
  govActive: { backgroundColor: "#111", borderColor: "#111" },
  govText: { fontSize: 12, color: "#555" },
  govTextActive: { color: "#FFF", fontWeight: "700" },
  primary: { height: 52, borderRadius: 12, backgroundColor: "#111", alignItems: "center", justifyContent: "center", marginTop: 10, shadowColor: "#000", shadowOpacity: 0.1, shadowRadius: 8, elevation: 3 },
  disabled: { opacity: 0.6 },
  primaryText: { color: "#FFF", fontSize: 15, fontWeight: "800" },
  switchRow: { flexDirection: "row-reverse", justifyContent: "center", gap: 6, marginTop: 24 },
  switchText: { fontSize: 13, color: "#777" },
  switchLink: { fontSize: 13, fontWeight: "800", color: "#E60023" },
  terms: { color: "#999", fontSize: 11, textAlign: "center", marginTop: 32, lineHeight: 18 }
});
