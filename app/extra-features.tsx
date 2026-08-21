import { useState } from "react";
import { Alert, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ScreenContainer } from "@/components/screen-container";
import { ApiClient } from "@/lib/api-client";

type GiftPreview = { id: number; receiver_name: string; amount: string; status: string };

export default function ExtraFeaturesScreen() {
  const [phone, setPhone] = useState("");
  const [amount, setAmount] = useState("");
  const [message, setMessage] = useState("");
  const [preview, setPreview] = useState<GiftPreview | null>(null);
  const [loading, setLoading] = useState(false);

  async function requestGiftConfirmation() {
    if (!phone.trim() || !amount.trim()) return Alert.alert("بيانات ناقصة", "أدخلي رقم هاتف المستلم والمبلغ.");
    setLoading(true);
    try {
      const result = await ApiClient.post<GiftPreview & { message?: string }>("/api/gifts/", { receiver_phone: phone.trim(), amount: amount.trim(), message: message.trim() });
      setPreview(result);
    } catch (error: any) {
      Alert.alert("تعذر التحقق", error?.message || "تعذر إنشاء طلب التحويل.");
    } finally {
      setLoading(false);
    }
  }

  async function confirmGift() {
    if (!preview) return;
    setLoading(true);
    try {
      await ApiClient.post(`/api/gifts/${preview.id}/confirm/`, {});
      Alert.alert("تم التحويل", `تم إرسال ${preview.amount} إلى ${preview.receiver_name} بنجاح.`);
      setPreview(null); setPhone(""); setAmount(""); setMessage("");
    } catch (error: any) {
      Alert.alert("تعذر إتمام التحويل", error?.message || "تحققي من رصيد المحفظة وحاولي مجددًا.");
    } finally {
      setLoading(false);
    }
  }

  async function cancelGift() {
    if (!preview) return;
    setLoading(true);
    try {
      await ApiClient.post(`/api/gifts/${preview.id}/cancel/`, {});
      setPreview(null);
    } catch (error: any) {
      Alert.alert("تعذر إلغاء الطلب", error?.message || "حاولي مجددًا.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <ScreenContainer edges={["top", "bottom", "left", "right"]} className="bg-[#F5F5F5]">
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}><MaterialIcons name="arrow-forward" size={25} color="#171717" /></TouchableOpacity>
        <Text style={styles.title}>إرسال هدية</Text>
        <View style={{ width: 25 }} />
      </View>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <View style={styles.intro}>
          <MaterialIcons name="card-giftcard" size={30} color="#E60023" />
          <Text style={styles.introTitle}>تحويل رصيد كهدية</Text>
          <Text style={styles.introText}>نرسل الطلب إلى الخادم أولًا، نتحقق من صاحب الرقم ورصيدك، ثم لا يتم الخصم إلا بعد تأكيدك النهائي.</Text>
        </View>
        {!preview ? <View style={styles.card}>
          <Text style={styles.heading}>بيانات المستلم</Text>
          <TextInput style={styles.input} placeholder="رقم هاتف المستلم" value={phone} onChangeText={setPhone} keyboardType="phone-pad" textAlign="right" />
          <TextInput style={styles.input} placeholder="المبلغ" value={amount} onChangeText={setAmount} keyboardType="decimal-pad" textAlign="right" />
          <TextInput style={styles.input} placeholder="رسالة الهدية (اختياري)" value={message} onChangeText={setMessage} textAlign="right" />
          <TouchableOpacity style={styles.button} onPress={requestGiftConfirmation} disabled={loading}>
            <Text style={styles.buttonText}>{loading ? "جارٍ التحقق..." : "متابعة والتحقق من المستلم"}</Text>
          </TouchableOpacity>
        </View> : <View style={styles.confirmCard}>
          <View style={styles.confirmIcon}><MaterialIcons name="verified-user" size={35} color="#168451" /></View>
          <Text style={styles.confirmTitle}>تأكيد تحويل الهدية</Text>
          <Text style={styles.confirmLabel}>سيتم التحويل إلى الحساب</Text>
          <Text style={styles.receiver}>{preview.receiver_name}</Text>
          <Text style={styles.phone}>رقم الهاتف: {phone}</Text>
          <View style={styles.amountBox}><Text style={styles.amountLabel}>المبلغ النهائي</Text><Text style={styles.amount}>{preview.amount} ر.ي</Text></View>
          <Text style={styles.warning}>بعد الضغط على «تأكيد التحويل» سيتم خصم المبلغ وإضافته إلى رصيد المستلم، ولا يمكن التراجع عن العملية.</Text>
          <TouchableOpacity style={styles.button} onPress={confirmGift} disabled={loading}><Text style={styles.buttonText}>{loading ? "جارٍ تنفيذ التحويل..." : "تأكيد التحويل النهائي"}</Text></TouchableOpacity>
          <TouchableOpacity style={styles.cancelButton} onPress={cancelGift} disabled={loading}><Text style={styles.cancelText}>إلغاء وعدم التحويل</Text></TouchableOpacity>
        </View>}
      </ScrollView>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  header: { padding: 16, backgroundColor: "#FFF", flexDirection: "row", justifyContent: "space-between", alignItems: "center", borderBottomWidth: 1, borderColor: "#EAEAEA" },
  title: { fontSize: 20, fontWeight: "900", color: "#171717" },
  content: { padding: 14, paddingBottom: 40 },
  intro: { backgroundColor: "#FFF8F8", borderWidth: 1, borderColor: "#F2D7D7", borderRadius: 12, padding: 16, alignItems: "flex-end", marginBottom: 14 },
  introTitle: { fontSize: 17, fontWeight: "900", color: "#171717", marginTop: 8, textAlign: "right" },
  introText: { fontSize: 12, lineHeight: 20, color: "#686868", textAlign: "right", marginTop: 5 },
  card: { backgroundColor: "#FFF", borderRadius: 12, padding: 16 },
  heading: { fontSize: 17, fontWeight: "900", textAlign: "right", marginBottom: 12, color: "#171717" },
  input: { backgroundColor: "#F7F7F7", borderWidth: 1, borderColor: "#E5E5E5", borderRadius: 8, padding: 13, marginBottom: 10, textAlign: "right", color: "#171717" },
  button: { backgroundColor: "#E60023", padding: 14, borderRadius: 8, alignItems: "center", marginTop: 5 },
  buttonText: { color: "#FFF", fontWeight: "900", fontSize: 14 },
  confirmCard: { backgroundColor: "#FFF", borderRadius: 14, padding: 20, alignItems: "center" },
  confirmIcon: { width: 68, height: 68, borderRadius: 34, backgroundColor: "#E9F7EF", alignItems: "center", justifyContent: "center" },
  confirmTitle: { fontSize: 20, fontWeight: "900", color: "#171717", marginTop: 12 },
  confirmLabel: { color: "#777", fontSize: 12, marginTop: 20 },
  receiver: { color: "#171717", fontSize: 21, fontWeight: "900", marginTop: 5 },
  phone: { color: "#777", fontSize: 12, marginTop: 5 },
  amountBox: { width: "100%", backgroundColor: "#F7F7F7", borderRadius: 10, padding: 15, marginTop: 20, alignItems: "center" },
  amountLabel: { color: "#777", fontSize: 12 },
  amount: { color: "#E60023", fontSize: 28, fontWeight: "900", marginTop: 3 },
  warning: { color: "#8D4B00", backgroundColor: "#FFF7E8", padding: 12, borderRadius: 8, fontSize: 12, lineHeight: 20, textAlign: "right", marginTop: 14 },
  cancelButton: { padding: 15, alignItems: "center" },
  cancelText: { color: "#777", fontWeight: "800", fontSize: 13 },
});
