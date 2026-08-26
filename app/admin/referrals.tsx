import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ActivityIndicator, FlatList, StyleSheet, Switch, Text, View } from "react-native";
import { useCallback, useEffect, useState } from "react";

import { AdminLayout, AdminEmptyState, Colors, Font, Radius, Shadow, Spacing } from "@/components/admin";
import { apiCall } from "@/lib/_core/api";

type Leader = { userId: number; name: string; phone: string; governorate: string; invitedCount: number; referralCode: string };

export default function AdminReferralsScreen() {
  const [leaders, setLeaders] = useState<Leader[]>([]);
  const [enabled, setEnabled] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [setting, data] = await Promise.all([
        apiCall<{ referral: { isEnabled: boolean } }>("/api/referrals/me").catch(() => ({ referral: { isEnabled: false } })),
        apiCall<{ referrals: Leader[] }>("/api/admin/referrals"),
      ]);
      setEnabled(setting.referral.isEnabled);
      setLeaders(data.referrals);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const toggle = async (value: boolean) => {
    setEnabled(value);
    try {
      await apiCall("/api/admin/referrals/settings", { method: "PATCH", body: JSON.stringify({ isEnabled: value }) });
    } catch { setEnabled(!value); }
  };

  return (
    <AdminLayout title="الدعوات والمكافآت">
      <View style={styles.settingCard}>
        <View style={styles.settingRow}>
          <Switch value={enabled} onValueChange={toggle} trackColor={{ true: Colors.primary }} />
          <View style={{ flex: 1 }}>
            <Text style={styles.settingTitle}>تفعيل زر دعوة العملاء</Text>
            <Text style={styles.settingHint}>يبقى مخفيًا في صفحة العميل إلى أن تفعّليه.</Text>
          </View>
        </View>
      </View>

      {loading ? (
        <ActivityIndicator color={Colors.primary} style={{ marginTop: 40 }} />
      ) : (
        <FlatList
          data={leaders}
          keyExtractor={(item) => String(item.userId)}
          contentContainerStyle={styles.list}
          renderItem={({ item }) => (
            <View style={styles.card}>
              <View style={styles.countWrap}>
                <Text style={styles.count}>{item.invitedCount}</Text>
                <Text style={styles.countLabel}>دعوة</Text>
              </View>
              <View style={styles.cardCopy}>
                <Text style={styles.cardName}>{item.name}</Text>
                <Text style={styles.cardMeta}>{item.governorate} · {item.phone}</Text>
              </View>
              <View style={styles.cardIcon}>
                <MaterialIcons name="group-add" size={20} color={Colors.success} />
              </View>
            </View>
          )}
          ListEmptyComponent={
            <AdminEmptyState
              icon="group-add"
              title="لا يوجد مدعوون بعد"
              description="ستظهر قائمة المدعوين هنا."
            />
          }
        />
      )}
    </AdminLayout>
  );
}

const styles = StyleSheet.create({
  settingCard: { backgroundColor: Colors.surface, marginHorizontal: Spacing.lg, marginTop: Spacing.lg, borderRadius: Radius.md, padding: Spacing.lg, ...Shadow.soft },
  settingRow: { flexDirection: "row-reverse", alignItems: "center", gap: Spacing.md },
  settingTitle: { color: Colors.text, ...Font.label, textAlign: "right" },
  settingHint: { color: Colors.textMuted, ...Font.tiny, textAlign: "right", marginTop: 2 },

  list: { padding: Spacing.lg, paddingBottom: Spacing["4xl"] },
  card: { flexDirection: "row-reverse", alignItems: "center", backgroundColor: Colors.surface, borderRadius: Radius.md, padding: Spacing.md, marginBottom: Spacing.sm, gap: Spacing.md, ...Shadow.soft },
  countWrap: { width: 52, alignItems: "center", justifyContent: "center" },
  count: { color: Colors.primary, fontSize: 20, fontWeight: "900" },
  countLabel: { color: Colors.textMuted, ...Font.tiny },
  cardCopy: { flex: 1, alignItems: "flex-end" },
  cardName: { color: Colors.text, ...Font.cardTitle },
  cardMeta: { color: Colors.textSecondary, ...Font.tiny, marginTop: Spacing.xs },
  cardIcon: { width: 40, height: 40, borderRadius: Radius.sm, backgroundColor: Colors.successLight, alignItems: "center", justifyContent: "center" },
});
