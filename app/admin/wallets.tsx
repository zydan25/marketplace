import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { Alert, FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useEffect, useState } from "react";

import { AdminLayout, AdminField, AdminEmptyState, Colors, Font, Radius, Shadow, Spacing, showToast } from "@/components/admin";
import { ApiClient } from "@/lib/api-client";
import { useAuth } from "@/hooks/use-auth";

type Wallet = { id: number; user?: { phone?: string; name?: string; role?: string }; balance: string; currency: string };

export default function AdminWalletsScreen() {
  const { user, isAuthenticated } = useAuth();
  const [wallets, setWallets] = useState<Wallet[]>([]);
  const [selected, setSelected] = useState<Wallet | null>(null);
  const [amount, setAmount] = useState("");
  const [reference, setReference] = useState("");
  const [note, setNote] = useState("");
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const data = await ApiClient.get<{ results?: Wallet[] }>("/api/wallets/");
      setWallets(data.results ?? []);
    } catch {
      Alert.alert("تعذر تحميل المحافظ", "حاولي تحديث الصفحة.");
    } finally { setLoading(false); }
  }

  useEffect(() => { if (isAuthenticated && user?.role === "admin") load(); }, [isAuthenticated, user?.role]);

  async function save() {
    if (!selected || !amount || Number(amount) <= 0) {
      Alert.alert("بيانات ناقصة", "اختاري محفظة وأدخلي مبلغًا موجبًا.");
      return;
    }
    try {
      await ApiClient.post(`/api/wallets/${selected.id}/admin_adjust/`, { amount, transaction_type: "adjustment", document_type: "receipt", reference, note });
      showToast("تم حفظ سند القبض بنجاح", "success");
      setAmount(""); setReference(""); setNote(""); await load();
    } catch (error) {
      Alert.alert("تعذر الحفظ", error instanceof Error ? error.message : "تحققي من صلاحية المدير.");
    }
  }

  return (
    <AdminLayout title="سندات القبض والمحافظ">
      <FlatList
        data={wallets}
        keyExtractor={(item) => String(item.id)}
        contentContainerStyle={styles.list}
        ListHeaderComponent={
          <View style={styles.form}>
            <Text style={styles.formTitle}>إضافة رصيد للعميل</Text>
            <Text style={styles.selectedLabel}>
              {selected ? `المحدد: ${selected.user?.phone} · ${selected.balance} ${selected.currency}` : "اختاري محفظة من القائمة"}
            </Text>
            <AdminField label="المبلغ" value={amount} onChangeText={setAmount} keyboardType="numeric" placeholder="0" />
            <AdminField label="رقم المستند" value={reference} onChangeText={setReference} placeholder="رقم سند القبض" />
            <AdminField label="ملاحظة" value={note} onChangeText={setNote} placeholder="ملاحظة داخلية (اختياري)" />
            <TouchableOpacity style={styles.saveBtn} onPress={save}>
              <Text style={styles.saveBtnText}>حفظ سند القبض</Text>
            </TouchableOpacity>
          </View>
        }
        renderItem={({ item }) => (
          <TouchableOpacity
            style={[styles.card, selected?.id === item.id && styles.cardSelected]}
            activeOpacity={0.7}
            onPress={() => setSelected(item)}
          >
            <View style={styles.cardIcon}>
              <MaterialIcons name="account-balance-wallet" size={20} color={Colors.success} />
            </View>
            <View style={styles.cardCopy}>
              <Text style={styles.cardPhone}>{item.user?.phone ?? "—"}</Text>
              <Text style={styles.cardRole}>{item.user?.role ?? "عميل"}</Text>
            </View>
            <Text style={styles.cardBalance}>{item.balance} {item.currency}</Text>
          </TouchableOpacity>
        )}
        ListEmptyComponent={
          <AdminEmptyState
            icon="account-balance-wallet"
            title="لا توجد محافظ"
            description="لم يتم إنشاء أي محافظ بعد."
          />
        }
      />
    </AdminLayout>
  );
}

const styles = StyleSheet.create({
  list: { padding: Spacing.lg, paddingBottom: Spacing["4xl"] },
  form: { backgroundColor: Colors.surface, borderRadius: Radius.md, padding: Spacing.xl, marginBottom: Spacing.md, ...Shadow.soft },
  formTitle: { color: Colors.text, ...Font.sectionTitle, textAlign: "right", marginBottom: Spacing.sm },
  selectedLabel: { color: Colors.success, ...Font.small, textAlign: "right", marginBottom: Spacing.lg },

  card: { flexDirection: "row-reverse", alignItems: "center", backgroundColor: Colors.surface, borderRadius: Radius.md, padding: Spacing.md, marginBottom: Spacing.sm, gap: Spacing.md, ...Shadow.soft },
  cardSelected: { borderWidth: 2, borderColor: Colors.primary },
  cardIcon: { width: 42, height: 42, borderRadius: Radius.sm, backgroundColor: Colors.successLight, alignItems: "center", justifyContent: "center" },
  cardCopy: { flex: 1, alignItems: "flex-end" },
  cardPhone: { color: Colors.text, ...Font.cardTitle },
  cardRole: { color: Colors.textMuted, ...Font.tiny, marginTop: Spacing.xs },
  cardBalance: { color: Colors.success, fontSize: 16, fontWeight: "900" },

  saveBtn: { height: 48, backgroundColor: Colors.primary, borderRadius: Radius.sm, alignItems: "center", justifyContent: "center", marginTop: Spacing.md },
  saveBtnText: { color: Colors.textInverse, ...Font.button },
});
