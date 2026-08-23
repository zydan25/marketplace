import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { Alert, Image, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import { useState } from "react";
import { ScreenContainer } from "@/components/screen-container";
import { djangoLogin } from "@/lib/django-api";
import * as Auth from "@/lib/_core/auth";

export default function LoginScreen() {
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const goAfterLogin = (role: "customer" | "vendor" | "admin") => {
    if (role === "vendor") return router.replace("/vendor" as never);
    if (role === "admin") return router.replace("/admin" as never);
    return router.replace("/(tabs)/" as never);
  };

  const submit = async () => {
    const normalizedPhone = phone.trim();
    if (!normalizedPhone || !password) {
      Alert.alert("بيانات ناقصة", "أدخل رقم الجوال وكلمة المرور.");
      return;
    }
    try {
      setLoading(true);
      const result = await djangoLogin(normalizedPhone, password);
      const userInfo = { ...result.user, lastSignedIn: new Date() } as Auth.User;
      await Auth.setUserInfo(userInfo);
      const storedToken = await Auth.getSessionToken();
      if (!storedToken || storedToken !== result.token) {
        throw new Error("تعذر حفظ جلسة الدخول في المتصفح.");
      }
      goAfterLogin(result.user.role);
    } catch (e) {
      Alert.alert("تعذر الدخول", e instanceof Error ? e.message : "حاول مرة أخرى.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScreenContainer edges={["top", "bottom"]} className="bg-[#FFF]">
      <View style={s.header}><TouchableOpacity style={s.close} onPress={() => router.back()}><MaterialIcons name="close" size={21} color="#111" /></TouchableOpacity></View>
      <ScrollView showsVerticalScrollIndicator={false} automaticallyAdjustKeyboardInsets keyboardShouldPersistTaps="handled" contentContainerStyle={s.content}>
        <Image source={require("@/assets/images/welcome-logo.png")} style={s.logo} resizeMode="contain" />
        <Text style={s.title}>تسجيل الدخول</Text>
        <Text style={s.sub}>أدخل رقم الجوال وكلمة المرور للوصول إلى حسابك.</Text>
        <View style={s.form}>
          <Field icon="phone-android" value={phone} onChangeText={setPhone} placeholder="رقم الهاتف" keyboardType="phone-pad" />
          <Field icon="lock-outline" value={password} onChangeText={setPassword} placeholder="كلمة المرور" secureTextEntry />
          <TouchableOpacity style={s.forgot} onPress={() => Alert.alert("استعادة كلمة المرور", "سنضيف استعادة كلمة المرور عبر رمز التحقق في المرحلة التالية.")}><Text style={s.forgotText}>نسيت كلمة المرور؟</Text></TouchableOpacity>
          <TouchableOpacity style={[s.button, loading && s.disabled]} disabled={loading} onPress={submit}><Text style={s.buttonText}>{loading ? "جارٍ الدخول..." : "تسجيل الدخول"}</Text></TouchableOpacity>
        </View>
        <View style={s.row}><Text style={s.rowText}>ليس لديك حساب؟</Text><TouchableOpacity onPress={() => router.replace("/register" as never)}><Text style={s.link}>إنشاء حساب</Text></TouchableOpacity></View>
      </ScrollView>
      <Text style={s.terms}>بتسجيل الدخول، أنت توافق على شروط الاستخدام وسياسة الخصوصية.</Text>
    </ScreenContainer>
  );
}

function Field({ icon, ...props }: { icon: "phone-android" | "lock-outline"; value: string; onChangeText: (v: string) => void; placeholder: string; secureTextEntry?: boolean; keyboardType?: "phone-pad" }) {
  return <View style={s.field}><TextInput {...props} style={s.input} textAlign="right" placeholderTextColor="#999" autoCapitalize="none"/><MaterialIcons name={icon} size={20} color="#777" /></View>;
}

const s = StyleSheet.create({
  header:{height:54,paddingHorizontal:16,justifyContent:"center"},close:{width:36,height:36,borderRadius:18,backgroundColor:"#F5F5F5",alignItems:"center",justifyContent:"center"},
  content:{paddingHorizontal:22,paddingTop:36,paddingBottom:70,maxWidth:430,width:"100%",alignSelf:"center"},logo:{width:68,height:68,alignSelf:"center",marginBottom:22},title:{fontSize:24,fontWeight:"900",textAlign:"center",color:"#111"},sub:{fontSize:12,color:"#777",textAlign:"center",marginTop:8,marginBottom:28,lineHeight:19},form:{width:"100%"},field:{height:48,borderRadius:12,backgroundColor:"#F8F8F8",borderWidth:1,borderColor:"#ECECEC",flexDirection:"row",alignItems:"center",paddingHorizontal:15,marginBottom:12},input:{flex:1,fontSize:14,writingDirection:"rtl",color:"#111",marginRight:10},forgot:{alignSelf:"flex-start",marginBottom:20},forgotText:{color:"#777",fontSize:11,textDecorationLine:"underline"},button:{height:48,borderRadius:12,backgroundColor:"#111",justifyContent:"center",alignItems:"center"},disabled:{opacity:.6},buttonText:{color:"#FFF",fontSize:14,fontWeight:"800"},row:{flexDirection:"row-reverse",justifyContent:"center",gap:6,marginTop:22},rowText:{fontSize:12,color:"#777"},link:{fontSize:12,fontWeight:"800",color:"#E60023"},terms:{textAlign:"center",color:"#999",fontSize:9,paddingHorizontal:28,paddingBottom:16},
});