import { useState } from "react";
import { Alert, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ScreenContainer } from "@/components/screen-container";
import { ApiClient } from "@/lib/api-client";

export default function ExtraFeaturesScreen() {
  const [phone, setPhone] = useState("");
  const [amount, setAmount] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function sendGift() {
    if (!phone || !amount) return Alert.alert("خطأ", "الرجاء إدخال رقم الهاتف والمبلغ");
    setLoading(true);
    try {
      await ApiClient.post("/api/gifts/", { receiver_phone: phone, amount: amount, message });
      Alert.alert("نجاح", "تم إرسال الهدية بنجاح");
      setPhone(""); setAmount(""); setMessage("");
    } catch (error: any) {
      Alert.alert("خطأ", error.message || "تعذر إرسال الهدية");
    } finally {
      setLoading(false);
    }
  }

  async function requestLoan() {
    if (!amount) return Alert.alert("خطأ", "الرجاء إدخال المبلغ");
    setLoading(true);
    try {
      await ApiClient.post("/api/loans/", { amount, reason: message });
      Alert.alert("نجاح", "تم تقديم طلب القرض بنجاح");
      setAmount(""); setMessage("");
    } catch (error: any) {
      Alert.alert("خطأ", error.message || "تعذر تقديم الطلب");
    } finally {
      setLoading(false);
    }
  }

  return (
    <ScreenContainer edges={["top", "bottom", "left", "right"]} className="bg-[#F5F5F5]">
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}><MaterialIcons name="arrow-forward" size={25} /></TouchableOpacity>
        <Text style={styles.title}>خدمات مالية</Text>
        <View style={{ width: 25 }} />
      </View>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.card}>
          <Text style={styles.heading}>إرسال هدية (تحويل رصيد)</Text>
          <TextInput style={styles.input} placeholder="رقم هاتف المستلم" value={phone} onChangeText={setPhone} keyboardType="phone-pad" textAlign="right" />
          <TextInput style={styles.input} placeholder="المبلغ" value={amount} onChangeText={setAmount} keyboardType="decimal-pad" textAlign="right" />
          <TextInput style={styles.input} placeholder="رسالة الهدية (اختياري)" value={message} onChangeText={setMessage} textAlign="right" />
          <TouchableOpacity style={styles.button} onPress={sendGift} disabled={loading}>
            <Text style={styles.buttonText}>{loading ? "جارٍ الإرسال..." : "إرسال الهدية"}</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.card}>
          <Text style={styles.heading}>طلب قرض / سلفة</Text>
          <TextInput style={styles.input} placeholder="المبلغ المطلوب" value={amount} onChangeText={setAmount} keyboardType="decimal-pad" textAlign="right" />
          <TextInput style={styles.input} placeholder="سبب الطلب" value={message} onChangeText={setMessage} textAlign="right" />
          <TouchableOpacity style={[styles.button, { backgroundColor: "#111" }]} onPress={requestLoan} disabled={loading}>
            <Text style={styles.buttonText}>{loading ? "جارٍ التقديم..." : "تقديم طلب قرض"}</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  header: { padding: 16, backgroundColor: "#FFF", flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  title: { fontSize: 20, fontWeight: "900" },
  content: { padding: 14, paddingBottom: 40 },
  card: { backgroundColor: "#FFF", borderRadius: 10, padding: 16, marginBottom: 14 },
  heading: { fontSize: 17, fontWeight: "900", textAlign: "right", marginBottom: 12 },
  input: { backgroundColor: "#F7F7F7", borderWidth: 1, borderColor: "#E5E5E5", borderRadius: 7, padding: 13, marginBottom: 10, textAlign: "right" },
  button: { backgroundColor: "#E60023", padding: 14, borderRadius: 7, alignItems: "center", marginTop: 5 },
  buttonText: { color: "#FFF", fontWeight: "900", fontSize: 15 },
});
