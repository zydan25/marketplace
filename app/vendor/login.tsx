import { useState } from "react";
import { Alert, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import { ScreenContainer } from "@/components/screen-container";
import { djangoLogin } from "@/lib/django-api";

export default function VendorLoginScreen() {
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit() {
    if (!phone.trim() || !password) return Alert.alert("بيانات ناقصة", "أدخل رقم الهاتف وكلمة المرور.");
    setLoading(true);
    try {
      const result = await djangoLogin(phone.trim(), password);
      if (result.user.role !== "vendor") throw new Error("هذا الحساب ليس حساب تاجر.");
      router.replace("/vendor" as never);
    } catch (error) {
      Alert.alert("تعذر الدخول", error instanceof Error ? error.message : "حدث خطأ غير متوقع");
    } finally {
      setLoading(false);
    }
  }

  return (
    <ScreenContainer edges={["top", "bottom", "left", "right"]} className="bg-[#F7F7F7]">
      <ScrollView contentContainerStyle={styles.container} automaticallyAdjustKeyboardInsets>
        <Text style={styles.kicker}>بوابة الشركاء</Text>
        <Text style={styles.title}>إدارة متجرك</Text>
        <Text style={styles.subtitle}>ادخل إلى لوحة التاجر لمتابعة المنتجات والطلبات والمبيعات.</Text>
        <TextInput style={styles.input} placeholder="رقم الهاتف" keyboardType="phone-pad" value={phone} onChangeText={setPhone} textAlign="right" />
        <TextInput style={styles.input} placeholder="كلمة المرور" secureTextEntry value={password} onChangeText={setPassword} textAlign="right" />
        <TouchableOpacity style={[styles.button, loading && styles.pressed]} onPress={submit} disabled={loading}>
          <Text style={styles.buttonText}>{loading ? "جارٍ الدخول..." : "دخول التاجر"}</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => router.back()} style={styles.back}><Text style={styles.backText}>العودة إلى المتجر</Text></TouchableOpacity>
      </ScrollView>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  container: { paddingHorizontal: 24, paddingTop: 40, paddingBottom: 80, maxWidth: 450, width: "100%", alignSelf: "center" },
  kicker: { color: "#E60023", fontSize: 14, fontWeight: "800", textAlign: "right" },
  title: { color: "#151515", fontSize: 34, fontWeight: "900", textAlign: "right", marginTop: 8 },
  subtitle: { color: "#777", fontSize: 15, lineHeight: 25, textAlign: "right", marginTop: 10, marginBottom: 30 },
  input: { backgroundColor: "#FFF", borderWidth: 1, borderColor: "#E5E5E5", borderRadius: 8, paddingHorizontal: 16, paddingVertical: 15, fontSize: 16, marginBottom: 12 },
  button: { backgroundColor: "#111", paddingVertical: 16, borderRadius: 8, alignItems: "center", marginTop: 8 },
  pressed: { opacity: 0.75, transform: [{ scale: 0.98 }] },
  buttonText: { color: "#FFF", fontSize: 17, fontWeight: "900" },
  back: { alignItems: "center", padding: 18 },
  backText: { color: "#555", fontSize: 14, fontWeight: "700" },
});
