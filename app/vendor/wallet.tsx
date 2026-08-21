import { useEffect, useState } from "react";
import { Alert, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ScreenContainer } from "@/components/screen-container";
import { djangoApi } from "@/lib/django-api";

type Wallet = { id: number; balance: string; currency: string; is_locked: boolean; transactions: { id: number; transaction_type: string; amount: string; balance_after: string; created_at: string }[] };

export default function VendorWalletScreen() {
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [amount, setAmount] = useState("");
  const [sending, setSending] = useState(false);

  async function load() {
    try { const data = await djangoApi<{ results?: Wallet[] }>("/api/wallets/"); setWallet(data.results?.[0] ?? null); } catch { setWallet(null); }
  }
  useEffect(() => { load(); }, []);

  async function requestTopUp() {
    if (!wallet || !amount || Number(amount) <= 0) return Alert.alert("أدخل مبلغًا صحيحًا", "اكتب المبلغ المطلوب شحنه.");
    setSending(true);
    try { await djangoApi(`/api/wallets/${wallet.id}/top_up_request/`, { method: "POST", body: JSON.stringify({ amount }) }); setAmount(""); Alert.alert("تم الإرسال", "أرسل طلب الشحن إلى الإدارة للمراجعة."); } catch (error) { Alert.alert("تعذر الإرسال", error instanceof Error ? error.message : "حدث خطأ"); } finally { setSending(false); }
  }

  return <ScreenContainer className="bg-[#F5F5F5]" edges={["top", "bottom", "left", "right"]}>
    <View style={styles.header}><TouchableOpacity onPress={() => router.back()}><MaterialIcons name="arrow-forward" size={25} /></TouchableOpacity><Text style={styles.title}>محفظة التاجر</Text><View style={{ width: 25 }} /></View>
    <View style={styles.balance}><Text style={styles.balanceLabel}>الرصيد المتاح</Text><Text style={styles.balanceValue}>{wallet?.balance ?? "0.00"} {wallet?.currency ?? "YER"}</Text></View>
    <View style={styles.card}><Text style={styles.heading}>طلب شحن الرصيد</Text><TextInput value={amount} onChangeText={setAmount} placeholder="المبلغ" keyboardType="decimal-pad" style={styles.input} textAlign="right" /><TouchableOpacity style={styles.button} onPress={requestTopUp} disabled={sending}><Text style={styles.buttonText}>{sending ? "جارٍ الإرسال..." : "إرسال الطلب"}</Text></TouchableOpacity></View>
    <Text style={styles.section}>آخر الحركات</Text>
    <View style={styles.card}>{wallet?.transactions?.length ? wallet.transactions.slice(0, 8).map((item) => <View key={item.id} style={styles.transaction}><Text style={styles.muted}>{item.transaction_type}</Text><Text style={styles.amount}>{item.amount} {wallet.currency}</Text></View>) : <Text style={styles.muted}>لا توجد حركات مسجلة.</Text>}</View>
  </ScreenContainer>;
}

const styles = StyleSheet.create({ header: { padding: 16, backgroundColor: "#FFF", flexDirection: "row", justifyContent: "space-between", alignItems: "center" }, title: { fontSize: 20, fontWeight: "900" }, balance: { backgroundColor: "#111", margin: 12, borderRadius: 12, padding: 22 }, balanceLabel: { color: "#BDBDBD", textAlign: "right", fontSize: 13 }, balanceValue: { color: "#FFF", textAlign: "right", fontSize: 29, fontWeight: "900", marginTop: 8 }, card: { backgroundColor: "#FFF", marginHorizontal: 12, marginBottom: 12, borderRadius: 10, padding: 16 }, heading: { fontSize: 17, fontWeight: "900", textAlign: "right", marginBottom: 12 }, input: { backgroundColor: "#F7F7F7", borderWidth: 1, borderColor: "#E5E5E5", borderRadius: 7, padding: 13, marginBottom: 10 }, button: { backgroundColor: "#E60023", padding: 14, borderRadius: 7, alignItems: "center" }, buttonText: { color: "#FFF", fontWeight: "900" }, section: { fontSize: 18, fontWeight: "900", textAlign: "right", marginHorizontal: 12, marginBottom: 9 }, transaction: { flexDirection: "row-reverse", justifyContent: "space-between", borderBottomWidth: 1, borderBottomColor: "#F0F0F0", paddingVertical: 11 }, amount: { color: "#168451", fontWeight: "900" }, muted: { color: "#777", fontSize: 13, textAlign: "right" } });
