import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { Alert, StyleSheet, Switch, Text, TouchableOpacity, View } from "react-native";
import { useEffect, useState } from "react";

import { AdminLayout, AdminField, Colors, Font, Radius, Shadow, Spacing, showToast } from "@/components/admin";
import { apiCall } from "@/lib/_core/api";

export default function PricingScreen() {
  const [markup, setMarkup] = useState("0");
  const [freeShipping, setFreeShipping] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    apiCall<{ outsideIbbMarkupPercent: number; freeShippingOutsideIbb: boolean }>("/api/pricing-settings").then((data) => {
      setMarkup(String(data.outsideIbbMarkupPercent));
      setFreeShipping(data.freeShippingOutsideIbb);
    });
  }, []);

  const save = async () => {
    try {
      setSaving(true);
      await apiCall("/api/admin/pricing-settings", {
        method: "PATCH",
        body: JSON.stringify({ outsideIbbMarkupPercent: Number(markup), freeShippingOutsideIbb: freeShipping }),
      });
      showToast("تم حفظ قاعدة الأسعار", "success");
    } catch (error) {
      Alert.alert("تعذر الحفظ", error instanceof Error ? error.message : "راجعي النسبة.");
    } finally { setSaving(false); }
  };

  return (
    <AdminLayout title="التحكم بالأسعار">
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <View style={styles.iconWrap}>
            <MaterialIcons name="payments" size={20} color={Colors.info} />
          </View>
          <Text style={styles.heading}>المحافظات خارج إب</Text>
        </View>
        <Text style={styles.copy}>تُضاف هذه النسبة إلى سعر الصنف للعملاء خارج إب. اتركيها 0 إذا أردت نفس الأسعار.</Text>

        <AdminField label="نسبة الزيادة %" value={markup} onChangeText={setMarkup} keyboardType="numeric" placeholder="0" />

        <View style={styles.switchRow}>
          <Switch value={freeShipping} onValueChange={setFreeShipping} trackColor={{ true: Colors.primary }} />
          <View style={{ flex: 1 }}>
            <Text style={styles.switchTitle}>توصيل مجاني خارج إب</Text>
            <Text style={styles.switchHint}>عند التفعيل لا يضاف رسم توصيل منفصل.</Text>
          </View>
        </View>

        <TouchableOpacity style={[styles.saveBtn, saving && styles.saveBtnDisabled]} disabled={saving} onPress={save}>
          <Text style={styles.saveBtnText}>{saving ? "جارِ الحفظ..." : "حفظ قاعدة الأسعار"}</Text>
        </TouchableOpacity>
      </View>
    </AdminLayout>
  );
}

const styles = StyleSheet.create({
  card: {
    margin: Spacing.lg,
    backgroundColor: Colors.surface,
    borderRadius: Radius.lg,
    padding: Spacing.xl,
    ...Shadow.soft,
  },
  cardHeader: { flexDirection: "row-reverse", alignItems: "center", gap: Spacing.md, marginBottom: Spacing.md },
  iconWrap: { width: 42, height: 42, borderRadius: Radius.sm, backgroundColor: Colors.infoLight, alignItems: "center", justifyContent: "center" },
  heading: { color: Colors.text, ...Font.sectionTitle },
  copy: { color: Colors.textSecondary, ...Font.small, lineHeight: 18, textAlign: "right", marginBottom: Spacing.lg },

  switchRow: { flexDirection: "row-reverse", alignItems: "center", gap: Spacing.md, paddingVertical: Spacing.lg, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: Colors.border },
  switchTitle: { color: Colors.text, ...Font.label, textAlign: "right" },
  switchHint: { color: Colors.textMuted, ...Font.tiny, textAlign: "right", marginTop: 2 },

  saveBtn: { height: 48, backgroundColor: Colors.primary, borderRadius: Radius.sm, alignItems: "center", justifyContent: "center", marginTop: Spacing.md, ...Shadow.raised },
  saveBtnDisabled: { opacity: 0.6 },
  saveBtnText: { color: Colors.textInverse, ...Font.button },
});
