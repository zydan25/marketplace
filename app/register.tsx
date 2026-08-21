import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { Alert, Image, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useState } from "react";
import { ScreenContainer } from "@/components/screen-container";
import * as Api from "@/lib/_core/api";
import * as Auth from "@/lib/_core/auth";
const governorates = ["أمانة العاصمة", "عدن", "أبين", "البيضاء", "الضالع", "الحديدة", "الجوف", "المهرة", "المحويت", "عمران", "ذمار", "حضرموت", "حجة", "إب", "لحج", "مأرب", "ريمة", "صعدة", "صنعاء", "شبوة", "سقطرى", "تعز"];
export default function RegisterScreen() {
  const { ref } = useLocalSearchParams<{ ref?: string }>(); const [v, setV] = useState({ firstName:"", secondName:"", thirdName:"", familyName:"", phone:"", password:"", governorate:"" }); const [open, setOpen] = useState(false); const [loading, setLoading] = useState(false); const update = (key: keyof typeof v) => (value: string) => setV((current) => ({ ...current, [key]: value }));
  const submit = async () => { try { setLoading(true); const result = await Api.registerWithPhone({ ...v, referralCode: ref }); await Auth.setSessionToken(result.sessionToken); await Auth.setUserInfo({ ...result.user, lastSignedIn: new Date(result.user.lastSignedIn) }); router.replace("/profile" as never); } catch (error) { Alert.alert("تعذر إنشاء الحساب", error instanceof Error ? error.message : "راجعي البيانات وحاولي مجددًا."); } finally { setLoading(false); } };
  return (
    <ScreenContainer edges={["top"]} className="bg-[#FFF]">
      <View style={s.header}>
        <TouchableOpacity style={s.back} onPress={() => router.back()}>
          <MaterialIcons name="arrow-forward" size={22} color="#111" />
        </TouchableOpacity>
        <Text style={s.headerTitle}>إنشاء حساب</Text>
        <View style={{ width: 36 }} />
      </View>
      <ScrollView contentContainerStyle={s.content} automaticallyAdjustKeyboardInsets>
        <Text style={s.sub}>أدخل بياناتك لإنشاء حساب جديد.</Text>
        
        <View style={s.two}>
          <Box placeholder="الاسم الأول" value={v.firstName} onChangeText={update("firstName")} />
          <Box placeholder="الاسم الثاني" value={v.secondName} onChangeText={update("secondName")} />
        </View>
        <View style={s.two}>
          <Box placeholder="الاسم الثالث" value={v.thirdName} onChangeText={update("thirdName")} />
          <Box placeholder="اللقب" value={v.familyName} onChangeText={update("familyName")} />
        </View>
        
        <Input placeholder="رقم الجوال (77X XXX XXX)" value={v.phone} onChangeText={update("phone")} keyboardType="phone-pad" />
        <Input placeholder="كلمة المرور (8 أحرف على الأقل)" value={v.password} onChangeText={update("password")} secureTextEntry />
        
        <TouchableOpacity style={s.select} onPress={() => setOpen(!open)}>
          <MaterialIcons name={open ? "keyboard-arrow-up" : "keyboard-arrow-down"} size={20} color="#777" />
          <Text style={[s.selectText, !v.governorate && s.placeholder]}>{v.governorate || "المحافظة"}</Text>
        </TouchableOpacity>
        
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
          <Text style={s.primaryText}>{loading ? "جارِ الإنشاء..." : "إنشاء حساب"}</Text>
        </TouchableOpacity>
        
        <View style={s.switchRow}>
          <Text style={s.switchText}>لديك حساب بالفعل؟</Text>
          <TouchableOpacity onPress={() => router.replace("/login" as never)}>
            <Text style={s.switchLink}>تسجيل الدخول</Text>
          </TouchableOpacity>
        </View>
        
        <Text style={s.terms}>بإنشاء الحساب، أنت توافق على شروط الاستخدام وسياسة الخصوصية.</Text>
      </ScrollView>
    </ScreenContainer>
  );
}

function Box({ value, onChangeText, placeholder }: { value: string; onChangeText: (v: string) => void; placeholder: string }) {
  return <TextInput value={value} onChangeText={onChangeText} placeholder={placeholder} style={s.box} textAlign="right" placeholderTextColor="#999" />;
}
function Input(props: { value: string; onChangeText: (v: string) => void; placeholder: string; secureTextEntry?: boolean; keyboardType?: "phone-pad" }) {
  return <TextInput {...props} style={s.input} textAlign="right" placeholderTextColor="#999" />;
}

const s = StyleSheet.create({
  header: { height: 54, paddingHorizontal: 20, flexDirection: "row", justifyContent: "space-between", alignItems: "center", borderBottomWidth: 1, borderColor: "#F5F5F5" },
  headerTitle: { fontSize: 16, fontWeight: "900", color: "#111" },
  back: { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F5F5F5", alignItems: "center", justifyContent: "center" },
  content: { padding: 24, paddingBottom: 80, maxWidth: 500, width: "100%", alignSelf: "center" },
  sub: { color: "#777", fontSize: 13, textAlign: "right", marginBottom: 24 },
  two: { flexDirection: "row-reverse", gap: 12, marginBottom: 14 },
  box: { flex: 1, height: 48, borderRadius: 12, backgroundColor: "#F9F9F9", borderWidth: 1, borderColor: "#EFEFEF", paddingHorizontal: 16, fontSize: 14, writingDirection: "rtl", color: "#111" },
  input: { height: 48, borderRadius: 12, backgroundColor: "#F9F9F9", borderWidth: 1, borderColor: "#EFEFEF", paddingHorizontal: 16, fontSize: 14, marginBottom: 14, writingDirection: "rtl", color: "#111" },
  select: { height: 48, borderRadius: 12, backgroundColor: "#F9F9F9", borderWidth: 1, borderColor: "#EFEFEF", paddingHorizontal: 16, flexDirection: "row", alignItems: "center", marginBottom: 14 },
  selectText: { flex: 1, textAlign: "right", fontSize: 14, color: "#111", marginRight: 8 },
  placeholder: { color: "#999" },
  govs: { flexDirection: "row-reverse", flexWrap: "wrap", gap: 8, padding: 12, backgroundColor: "#F9F9F9", borderRadius: 12, borderWidth: 1, borderColor: "#EFEFEF", marginBottom: 14 },
  gov: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 20, backgroundColor: "#FFF", borderWidth: 1, borderColor: "#DDD" },
  govActive: { backgroundColor: "#111", borderColor: "#111" },
  govText: { fontSize: 12, color: "#555" },
  govTextActive: { color: "#FFF", fontWeight: "700" },
  primary: { height: 48, borderRadius: 12, backgroundColor: "#111", alignItems: "center", justifyContent: "center", marginTop: 10 },
  disabled: { opacity: 0.6 },
  primaryText: { color: "#FFF", fontSize: 15, fontWeight: "800" },
  switchRow: { flexDirection: "row-reverse", justifyContent: "center", gap: 6, marginTop: 24 },
  switchText: { fontSize: 13, color: "#777" },
  switchLink: { fontSize: 13, fontWeight: "800", color: "#E60023" },
  terms: { color: "#999", fontSize: 10, textAlign: "center", marginTop: 32 }
});
