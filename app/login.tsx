import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { Alert, Image, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import { useState } from "react";
import { ScreenContainer } from "@/components/screen-container";
import * as Api from "@/lib/_core/api";
import * as Auth from "@/lib/_core/auth";

export default function LoginScreen() {
  const [phone,setPhone]=useState(""); const [password,setPassword]=useState(""); const [loading,setLoading]=useState(false);
  const submit=async()=>{ if(!phone.trim()||!password) return Alert.alert("بيانات ناقصة","أدخلي رقم الجوال وكلمة المرور."); try{setLoading(true);const r=await Api.loginWithPhone(phone,password);await Auth.setSessionToken(r.sessionToken);await Auth.setUserInfo({...r.user,lastSignedIn:new Date(r.user.lastSignedIn)});if(r.user.role==="vendor"){router.replace("/vendor" as never)}else{router.replace("/profile" as never)}}catch(e){Alert.alert("تعذر الدخول",e instanceof Error?e.message:"حاولي مرة أخرى.")}finally{setLoading(false)}};
  return (
    <ScreenContainer edges={["top"]} className="bg-[#FFF]">
      <View style={s.header}>
        <TouchableOpacity style={s.close} onPress={() => router.back()}>
          <MaterialIcons name="close" size={22} color="#111" />
        </TouchableOpacity>
      </View>
      <ScrollView contentContainerStyle={s.content} automaticallyAdjustKeyboardInsets>
        <Image source={require("@/assets/images/welcome-logo.png")} style={s.logo} resizeMode="contain" />
        <Text style={s.title}>تسجيل الدخول</Text>
        <Text style={s.sub}>أدخل رقم الجوال وكلمة المرور للوصول إلى حسابك.</Text>
        
        <View style={s.form}>
          <Field icon="phone-android" value={phone} onChangeText={setPhone} placeholder="رقم الهاتف" keyboardType="phone-pad" />
          <Field icon="lock-outline" value={password} onChangeText={setPassword} placeholder="كلمة المرور" secureTextEntry />
          
          <TouchableOpacity style={s.forgot}>
            <Text style={s.forgotText}>نسيت كلمة المرور؟</Text>
          </TouchableOpacity>

          <TouchableOpacity style={[s.button, loading && s.disabled]} disabled={loading} onPress={submit}>
            <Text style={s.buttonText}>{loading ? "جارِ الدخول..." : "تسجيل الدخول"}</Text>
          </TouchableOpacity>
        </View>

        <View style={s.row}>
          <Text style={s.rowText}>ليس لديك حساب؟</Text>
          <TouchableOpacity onPress={() => router.replace("/register" as never)}>
            <Text style={s.link}>إنشاء حساب</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
      <Text style={s.terms}>بتسجيل الدخول، أنت توافق على شروط الاستخدام وسياسة الخصوصية.</Text>
    </ScreenContainer>
  );
}

function Field({ icon, ...props }: { icon: "phone-android" | "lock-outline"; value: string; onChangeText: (v: string) => void; placeholder: string; secureTextEntry?: boolean; keyboardType?: "phone-pad" }) {
  return (
    <View style={s.field}>
      <TextInput {...props} style={s.input} textAlign="right" placeholderTextColor="#999" />
      <MaterialIcons name={icon} size={20} color="#777" />
    </View>
  );
}

const s = StyleSheet.create({
  header: { height: 54, paddingHorizontal: 20, justifyContent: "center" },
  close: { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F5F5F5", alignItems: "center", justifyContent: "center" },
  content: { paddingHorizontal: 24, paddingTop: 40, paddingBottom: 80, maxWidth: 400, width: "100%", alignSelf: "center" },
  logo: { width: 70, height: 70, alignSelf: "center", marginBottom: 24 },
  title: { fontSize: 24, fontWeight: "900", textAlign: "center", color: "#111" },
  sub: { fontSize: 13, color: "#777", textAlign: "center", marginTop: 8, marginBottom: 32 },
  form: { width: "100%" },
  field: { height: 48, borderRadius: 12, backgroundColor: "#F9F9F9", borderWidth: 1, borderColor: "#EFEFEF", flexDirection: "row", alignItems: "center", paddingHorizontal: 16, marginBottom: 14 },
  input: { flex: 1, fontSize: 14, writingDirection: "rtl", color: "#111", marginRight: 10 },
  forgot: { alignSelf: "flex-start", marginBottom: 24 },
  forgotText: { color: "#777", fontSize: 12, textDecorationLine: "underline" },
  button: { height: 48, borderRadius: 12, backgroundColor: "#111", justifyContent: "center", alignItems: "center" },
  disabled: { opacity: 0.6 },
  buttonText: { color: "#FFF", fontSize: 15, fontWeight: "800" },
  row: { flexDirection: "row-reverse", justifyContent: "center", gap: 6, marginTop: 24 },
  rowText: { fontSize: 13, color: "#777" },
  link: { fontSize: 13, fontWeight: "800", color: "#E60023" },
  terms: { textAlign: "center", color: "#999", fontSize: 10, paddingHorizontal: 30, paddingBottom: 20 }
});
