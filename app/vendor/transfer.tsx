import { useState } from "react";
import { ActivityIndicator, Alert, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ScreenContainer } from "@/components/screen-container";
import { djangoApi } from "@/lib/django-api";

export default function VendorTransferScreen() {
  const [phone, setPhone] = useState("");
  const [amount, setAmount] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleTransfer() {
    if (!phone.trim() || !amount.trim()) {
      return Alert.alert("بيانات ناقصة", "يرجى إدخال رقم الهاتف والمبلغ.");
    }
    
    Alert.alert(
      "تأكيد التحويل",
      `هل أنت متأكد من تحويل مبلغ ${amount} إلى الرقم ${phone}؟ لا يمكن التراجع عن هذه العملية.`,
      [
        { text: "إلغاء", style: "cancel" },
        { 
          text: "تأكيد التحويل", 
          style: "destructive",
          onPress: async () => {
            setLoading(true);
            try {
              const gift = await djangoApi<{ id: number; receiver_name?: string; amount: string; status: string }>("/api/gifts/", {
                method: "POST",
                body: JSON.stringify({ receiver_phone: phone.trim(), amount: Number(amount) })
              });
              await djangoApi(`/api/gifts/${gift.id}/confirm/`, { method: "POST" });
              Alert.alert("تم بنجاح", `تم تحويل ${gift.amount} إلى ${gift.receiver_name || phone.trim()} بنجاح.`);
              setPhone("");
              setAmount("");
            } catch (error) {
              Alert.alert(
                "تعذر التحويل", 
                error instanceof Error ? error.message : "المحفظة التي تم طلب رقمها غير موجودة أو الرصيد غير كافٍ."
              );
            } finally {
              setLoading(false);
            }
          }
        }
      ]
    );
  }

  return (
    <ScreenContainer edges={["top", "bottom", "left", "right"]} className="bg-[#F7F7F7]">
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.headerBtn}>
          <MaterialIcons name="arrow-forward" size={24} color="#111" />
        </TouchableOpacity>
        <Text style={styles.title}>إهداء / تحويل رصيد</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView style={styles.scroll} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <View style={styles.card}>
          <View style={styles.iconBox}>
            <MaterialIcons name="card-giftcard" size={48} color="#E60023" />
          </View>
          <Text style={styles.cardTitle}>تحويل الرصيد لعميل أو تاجر آخر</Text>
          <Text style={styles.cardDesc}>
            يمكنك تحويل أي مبلغ من رصيدك المتاح إلى أي شخص لديه حساب في شبيك باستخدام رقم هاتفه.
          </Text>
          
          <View style={styles.formGroup}>
            <Text style={styles.label}>رقم هاتف المستلم</Text>
            <TextInput
              style={styles.input}
              placeholder="مثال: 77XXXXXXX"
              keyboardType="phone-pad"
              value={phone}
              onChangeText={setPhone}
              textAlign="right"
            />
          </View>
          
          <View style={styles.formGroup}>
            <Text style={styles.label}>المبلغ المراد تحويله</Text>
            <TextInput
              style={styles.input}
              placeholder="المبلغ بالريال اليمني"
              keyboardType="numeric"
              value={amount}
              onChangeText={setAmount}
              textAlign="right"
            />
          </View>
          
          <TouchableOpacity 
            style={[styles.submitBtn, (!phone || !amount || loading) && styles.submitBtnDisabled]} 
            onPress={handleTransfer}
            disabled={!phone || !amount || loading}
          >
            {loading ? (
              <ActivityIndicator color="#FFF" />
            ) : (
              <Text style={styles.submitBtnText}>تحويل الآن</Text>
            )}
          </TouchableOpacity>
        </View>
      </ScrollView>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  header: { height: 60, paddingHorizontal: 16, flexDirection: "row-reverse", justifyContent: "space-between", alignItems: "center", backgroundColor: "#FFF", borderBottomWidth: 1, borderColor: "#EEE" },
  headerBtn: { padding: 8 },
  title: { fontSize: 18, fontWeight: "900", color: "#111" },
  scroll: { flex: 1 },
  content: { padding: 16, paddingBottom: 100 },
  card: { backgroundColor: "#FFF", borderRadius: 16, padding: 24, borderWidth: 1, borderColor: "#EEE", alignItems: "center" },
  iconBox: { width: 80, height: 80, borderRadius: 40, backgroundColor: "#FFF5F5", alignItems: "center", justifyContent: "center", marginBottom: 16 },
  cardTitle: { fontSize: 18, fontWeight: "900", color: "#111", textAlign: "center", marginBottom: 8 },
  cardDesc: { fontSize: 13, color: "#777", textAlign: "center", lineHeight: 20, marginBottom: 24 },
  formGroup: { width: "100%", marginBottom: 16 },
  label: { fontSize: 14, fontWeight: "800", color: "#333", textAlign: "right", marginBottom: 8 },
  input: { width: "100%", height: 52, borderWidth: 1, borderColor: "#E5E5E5", borderRadius: 12, paddingHorizontal: 16, fontSize: 15, textAlign: "right", backgroundColor: "#FAFAFA" },
  submitBtn: { width: "100%", height: 52, backgroundColor: "#111", borderRadius: 26, justifyContent: "center", alignItems: "center", marginTop: 8 },
  submitBtnDisabled: { backgroundColor: "#CCC" },
  submitBtnText: { color: "#FFF", fontSize: 16, fontWeight: "900" },
});
