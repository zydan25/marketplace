import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { Alert, FlatList, Image, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useEffect, useState } from "react";

import { AdminLayout, AdminField, Colors, Font, Radius, Shadow, Spacing, showToast } from "@/components/admin";
import { apiCall } from "@/lib/_core/api";
import { getAdminProducts, type StoreProduct } from "@/lib/product-api";

type Audience = "governorate" | "single" | "selected";
const governorates = ["أمانة العاصمة", "عدن", "تعز", "الحديدة", "إب", "ذمار", "حضرموت", "صنعاء", "عمران", "حجة", "صعدة", "مأرب", "شبوة", "الجوف", "لحج", "أبين", "الضالع", "ريمة", "المحويت", "سقطرى", "المهرة", "البيضاء"];

export default function AdminNotificationsScreen() {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [audience, setAudience] = useState<Audience>("governorate");
  const [governorate, setGovernorate] = useState(governorates[0]);
  const [userIds, setUserIds] = useState("");
  const [products, setProducts] = useState<StoreProduct[]>([]);
  const [selected, setSelected] = useState<StoreProduct | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => { getAdminProducts().then(setProducts).catch(() => setProducts([])); }, []);

  const send = async () => {
    try {
      setSaving(true);
      await apiCall("/api/admin/marketing-notifications", {
        method: "POST",
        body: JSON.stringify({
          title, body,
          audienceType: audience,
          governorate: audience === "governorate" ? governorate : undefined,
          userIds: userIds.split(/[،,\s]+/).map(Number).filter(Number.isInteger),
          productId: selected ? Number(selected.id) : undefined,
          imageUrl: selected?.images[0]?.url,
        }),
      });
      showToast("تم إرسال الإشعار بنجاح", "success");
      setTitle(""); setBody(""); setUserIds(""); setSelected(null);
    } catch (error) {
      Alert.alert("تعذر الإرسال", error instanceof Error ? error.message : "راجعي البيانات.");
    } finally { setSaving(false); }
  };

  const audienceChips: { key: Audience; label: string; icon: string }[] = [
    { key: "governorate", label: "محافظة", icon: "location-on" },
    { key: "single", label: "عميل واحد", icon: "person" },
    { key: "selected", label: "عملاء محددون", icon: "people" },
  ];

  return (
    <AdminLayout title="إرسال إشعار">
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <Text style={styles.intro}>يمكنك إرسال عنوان وشرح وصورة المنتج؛ الضغط على الإشعار يفتح الصنف المرتبط.</Text>

        <AdminField label="عنوان الإشعار" value={title} onChangeText={setTitle} placeholder="مثال: تخفيض اليوم" />
        <AdminField label="شرح الإشعار" value={body} onChangeText={setBody} placeholder="نص الإشعار الموجه للعملاء" multiline numberOfLines={3} />

        <Text style={styles.fieldLabel}>نوع الجمهور</Text>
        <View style={styles.chipRow}>
          {audienceChips.map((chip) => (
            <TouchableOpacity key={chip.key} style={[styles.chip, audience === chip.key && styles.chipActive]} onPress={() => setAudience(chip.key)}>
              <MaterialIcons name={chip.icon as never} size={14} color={audience === chip.key ? Colors.textInverse : Colors.textSecondary} />
              <Text style={[styles.chipText, audience === chip.key && styles.chipTextActive]}>{chip.label}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {audience === "governorate" && (
          <View style={styles.govGrid}>
            {governorates.map((gov) => (
              <TouchableOpacity key={gov} style={[styles.govChip, governorate === gov && styles.govChipActive]} onPress={() => setGovernorate(gov)}>
                <Text style={[styles.govText, governorate === gov && styles.govTextActive]}>{gov}</Text>
              </TouchableOpacity>
            ))}
          </View>
        )}

        {audience === "single" && <AdminField label="رقم العميل" value={userIds} onChangeText={setUserIds} placeholder="رقم الهوية" keyboardType="numeric" />}

        {audience === "selected" && <AdminField label="أرقام العملاء" value={userIds} onChangeText={setUserIds} placeholder="123، 456، 789" helper="افصلي الأرقام بالفاصلة." />}

        <Text style={styles.fieldLabel}>صورة المنتج (اختياري)</Text>
        <FlatList
          horizontal
          data={products}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.productList}
          showsHorizontalScrollIndicator={false}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={[styles.productCard, selected?.id === item.id && styles.productCardSelected]}
              onPress={() => setSelected(selected?.id === item.id ? null : item)}
            >
              {item.images[0]?.url ? (
                <Image source={{ uri: item.images[0].url }} style={styles.productImage} />
              ) : (
                <View style={styles.productNoImage}>
                  <MaterialIcons name="image" size={20} color={Colors.textMuted} />
                </View>
              )}
              <Text style={styles.productName} numberOfLines={1}>{item.name}</Text>
              <Text style={styles.productCode}>{item.productCode}</Text>
            </TouchableOpacity>
          )}
        />

        <TouchableOpacity style={[styles.sendBtn, saving && styles.sendBtnDisabled]} disabled={saving} onPress={send}>
          <MaterialIcons name="send" size={18} color={Colors.textInverse} />
          <Text style={styles.sendBtnText}>{saving ? "جارِ الإرسال..." : "إرسال الإشعار"}</Text>
        </TouchableOpacity>
      </ScrollView>
    </AdminLayout>
  );
}

const styles = StyleSheet.create({
  content: { padding: Spacing.lg, paddingBottom: Spacing["4xl"] },
  intro: { color: Colors.textSecondary, ...Font.small, textAlign: "right", lineHeight: 18, marginBottom: Spacing.lg },
  fieldLabel: { color: Colors.text, ...Font.label, textAlign: "right", marginBottom: Spacing.sm },
  chipRow: { flexDirection: "row-reverse", gap: Spacing.sm, marginBottom: Spacing.lg },
  chip: { flexDirection: "row", alignItems: "center", gap: Spacing.xs, borderRadius: Radius.sm, borderWidth: 1, borderColor: Colors.border, paddingHorizontal: Spacing.md, paddingVertical: Spacing.sm, backgroundColor: Colors.surface },
  chipActive: { backgroundColor: Colors.black, borderColor: Colors.black },
  chipText: { color: Colors.textSecondary, ...Font.chip },
  chipTextActive: { color: Colors.textInverse, fontWeight: "700" },

  govGrid: { flexDirection: "row-reverse", flexWrap: "wrap", gap: Spacing.sm, marginBottom: Spacing.lg },
  govChip: { borderRadius: Radius.sm, borderWidth: 1, borderColor: Colors.border, paddingHorizontal: Spacing.md, paddingVertical: Spacing.sm, backgroundColor: Colors.surface },
  govChipActive: { backgroundColor: Colors.primary, borderColor: Colors.primary },
  govText: { color: Colors.textSecondary, ...Font.tiny },
  govTextActive: { color: Colors.textInverse, fontWeight: "700" },

  productList: { gap: Spacing.sm, paddingVertical: Spacing.sm, paddingBottom: Spacing.lg },
  productCard: { width: 100, backgroundColor: Colors.surface, borderRadius: Radius.sm, padding: Spacing.xs, borderWidth: 1, borderColor: Colors.border, ...Shadow.soft },
  productCardSelected: { borderColor: Colors.primary, borderWidth: 2 },
  productImage: { width: "100%", height: 100, borderRadius: Radius.sm, resizeMode: "cover" as const },
  productNoImage: { width: "100%", height: 100, borderRadius: Radius.sm, backgroundColor: Colors.surfaceAlt, alignItems: "center", justifyContent: "center" },
  productName: { color: Colors.text, ...Font.tiny, textAlign: "right", marginTop: Spacing.xs },
  productCode: { color: Colors.primary, ...Font.tiny, textAlign: "right", marginTop: 2 },

  sendBtn: { height: 52, backgroundColor: Colors.primary, borderRadius: Radius.sm, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: Spacing.sm, marginTop: Spacing.md, ...Shadow.raised },
  sendBtnDisabled: { opacity: 0.6 },
  sendBtnText: { color: Colors.textInverse, ...Font.button },
});
