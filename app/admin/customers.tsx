import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { Alert, FlatList, StyleSheet, Switch, Text, TextInput, TouchableOpacity, View } from "react-native";
import { useEffect, useMemo, useState } from "react";

import { AdminLayout, AdminField, AdminEmptyState, Colors, Font, Radius, Shadow, Spacing, showToast } from "@/components/admin";
import { useAuth } from "@/hooks/use-auth";
import { assignCustomerReward, getAdminCustomer, getAdminCustomers, setCustomerRewardActive, type CustomerProfile, type CustomerRewardPayload, type CustomerSummary } from "@/lib/customer-api";
import { formatYER } from "@/lib/catalog";

type RewardForm = { rewardType: CustomerRewardPayload["rewardType"]; title: string; couponCode: string; discountType: CustomerRewardPayload["discountType"]; discountValue: string; minimumOrderAmount: string; minimumQuantity: string; giftName: string; isActive: boolean };
const emptyForm: RewardForm = { rewardType: "coupon", title: "", couponCode: "", discountType: "fixed", discountValue: "", minimumOrderAmount: "", minimumQuantity: "", giftName: "", isActive: true };
const rewardNames = { gift: "هدية", coupon: "كوبون", order_threshold: "حد أدنى للشراء", quantity_threshold: "خصم كمية" } as const;

export default function CustomersAdminScreen() {
  const { user, isAuthenticated } = useAuth();
  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [selected, setSelected] = useState<CustomerProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [governorate, setGovernorate] = useState("الكل");
  const [search, setSearch] = useState("");
  const [form, setForm] = useState<RewardForm>(emptyForm);

  const load = async () => { try { setLoading(true); setCustomers(await getAdminCustomers()); } catch (error) { Alert.alert("تعذر تحميل العملاء", error instanceof Error ? error.message : "حاولي مرة أخرى."); } finally { setLoading(false); } };
  useEffect(() => { if (isAuthenticated && user?.role === "admin") load(); }, [isAuthenticated, user?.role]);

  const governorates = useMemo(() => ["الكل", ...[...new Set(customers.map((customer) => customer.governorate))]], [customers]);
  const filtered = useMemo(() => customers.filter((customer) => (governorate === "الكل" || customer.governorate === governorate) && `${customer.name} ${customer.phone}`.includes(search.trim())), [customers, governorate, search]);

  const openCustomer = async (id: number) => { try { setLoading(true); setSelected(await getAdminCustomer(id)); setForm(emptyForm); } catch (error) { Alert.alert("تعذر فتح ملف العميل", error instanceof Error ? error.message : "حاولي مرة أخرى."); } finally { setLoading(false); } };

  const saveReward = async () => { if (!selected || !form.title.trim()) { Alert.alert("بيانات ناقصة", "أدخلي عنوان الحافز أولًا."); return; } const payload: CustomerRewardPayload = { rewardType: form.rewardType, title: form.title.trim(), couponCode: form.couponCode.trim().toUpperCase() || undefined, discountType: form.discountType, discountValue: Number(form.discountValue) || 0, minimumOrderAmount: Number(form.minimumOrderAmount) || 0, minimumQuantity: Number(form.minimumQuantity) || 0, giftName: form.giftName.trim() || undefined, isActive: form.isActive }; try { setSaving(true); await assignCustomerReward(selected.id, payload); setSelected(await getAdminCustomer(selected.id)); setForm(emptyForm); showToast("تمت إضافة الحافز بنجاح", "success"); } catch (error) { Alert.alert("تعذر إرسال الحافز", error instanceof Error ? error.message : "راجعي البيانات وحاولي مرة أخرى."); } finally { setSaving(false); } };

  const toggleReward = async (rewardId: number, isActive: boolean) => { if (!selected) return; try { await setCustomerRewardActive(rewardId, isActive); setSelected(await getAdminCustomer(selected.id)); } catch { Alert.alert("تعذر تحديث الحافز", "حاولي مرة أخرى."); } };

  if (selected) {
    const types = Object.keys(rewardNames) as RewardForm["rewardType"][];
    return (
      <AdminLayout title="ملف العميل">
        <FlatList
          data={selected.rewards}
          keyExtractor={(item) => String(item.id)}
          contentContainerStyle={styles.detailList}
          ListHeaderComponent={
            <View>
              <View style={styles.profileCard}>
                <View style={styles.profileAvatar}>
                  <Text style={styles.profileInitial}>{selected.name.slice(0, 1)}</Text>
                </View>
                <View style={styles.profileCopy}>
                  <Text style={styles.profileName}>{selected.name}</Text>
                  <Text style={styles.profileMeta}>{selected.phone} · {selected.governorate}</Text>
                </View>
              </View>
              <View style={styles.rewardSection}>
                <Text style={styles.sectionTitle}>إضافة حافز جديد</Text>
                <View style={styles.chipRow}>
                  {types.map((type) => (
                    <TouchableOpacity key={type} style={[styles.chip, form.rewardType === type && styles.chipActive]} onPress={() => setForm((v) => ({ ...v, rewardType: type }))}>
                      <Text style={[styles.chipText, form.rewardType === type && styles.chipTextActive]}>{rewardNames[type]}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
                <AdminField label="العنوان" value={form.title} onChangeText={(title) => setForm((v) => ({ ...v, title }))} placeholder="مثال: خصم خاص" />
                {form.rewardType !== "gift" && <AdminField label="كود الكوبون" value={form.couponCode} onChangeText={(couponCode) => setForm((v) => ({ ...v, couponCode }))} placeholder="اختياري" />}
                {form.rewardType !== "gift" && (
                  <View style={styles.twoFields}>
                    <AdminField compact label="قيمة الخصم" value={form.discountValue} onChangeText={(discountValue) => setForm((v) => ({ ...v, discountValue }))} keyboardType="numeric" placeholder="0" />
                    <AdminField compact label="الحد الأدنى" value={form.minimumOrderAmount} onChangeText={(minimumOrderAmount) => setForm((v) => ({ ...v, minimumOrderAmount }))} keyboardType="numeric" placeholder="0" />
                  </View>
                )}
                {form.rewardType === "gift" && <AdminField label="اسم الهدية" value={form.giftName} onChangeText={(giftName) => setForm((v) => ({ ...v, giftName }))} placeholder="مثال: شاحن لاسلكي" />}
                <TouchableOpacity style={styles.saveBtn} onPress={saveReward} disabled={saving}>
                  <Text style={styles.saveBtnText}>{saving ? "جارِ الحفظ..." : "إضافة الحافز"}</Text>
                </TouchableOpacity>
              </View>
              {selected.rewards.length > 0 && <Text style={styles.sectionTitle}>الحوافز الحالية</Text>}
            </View>
          }
          renderItem={({ item }) => (
            <View style={styles.rewardCard}>
              <Switch value={item.isActive} onValueChange={(value) => toggleReward(item.id, value)} trackColor={{ true: Colors.primary }} />
              <View style={styles.rewardCopy}>
                <Text style={styles.rewardTitle}>{item.title}</Text>
                <Text style={styles.rewardMeta}>{rewardNames[item.rewardType]}{item.couponCode ? ` · ${item.couponCode}` : ""}{item.discountValue ? ` · ${item.discountType === "percent" ? `${item.discountValue}%` : formatYER(item.discountValue)}` : ""}</Text>
              </View>
            </View>
          )}
          ListEmptyComponent={<Text style={styles.empty}>لا توجد حوافز بعد.</Text>}
        />
      </AdminLayout>
    );
  }

  return (
    <AdminLayout title="العملاء">
      <View style={styles.searchWrap}>
        <MaterialIcons name="search" size={18} color={Colors.textMuted} />
        <TextInput value={search} onChangeText={setSearch} placeholder="ابحثي بالاسم أو رقم الهاتف" placeholderTextColor={Colors.textMuted} style={styles.searchInput} textAlign="right" />
      </View>
      <FlatList
        horizontal
        inverted
        data={governorates}
        keyExtractor={(item) => item}
        contentContainerStyle={styles.govList}
        showsHorizontalScrollIndicator={false}
        renderItem={({ item }) => (
          <TouchableOpacity onPress={() => setGovernorate(item)} style={[styles.chip, item === governorate && styles.chipActive]}>
            <Text style={[styles.chipText, item === governorate && styles.chipTextActive]}>{item}</Text>
          </TouchableOpacity>
        )}
      />
      <FlatList
        data={filtered}
        keyExtractor={(item) => String(item.id)}
        contentContainerStyle={styles.list}
        refreshing={loading}
        onRefresh={load}
        renderItem={({ item }) => (
          <TouchableOpacity style={styles.card} activeOpacity={0.7} onPress={() => openCustomer(item.id)}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>{item.name.slice(0, 1)}</Text>
            </View>
            <View style={styles.cardCopy}>
              <Text style={styles.cardName}>{item.name}</Text>
              <Text style={styles.cardMeta}>{item.phone} · {item.governorate}</Text>
              <Text style={styles.cardRewards}>{item.rewardCount ? `${item.rewardCount} حوافز مفعلة` : "لا توجد حوافز بعد"}</Text>
            </View>
            <MaterialIcons name="chevron-left" size={20} color={Colors.textMuted} />
          </TouchableOpacity>
        )}
        ListEmptyComponent={
          !loading ? (
            <AdminEmptyState
              icon="people-outline"
              title="لا يوجد عملاء"
              description="لا يوجد عملاء مطابقون لهذا الفرز بعد."
            />
          ) : null
        }
      />
    </AdminLayout>
  );
}

const styles = StyleSheet.create({
  searchWrap: { ...StyleSheet.flatten([{ backgroundColor: Colors.surface, marginHorizontal: Spacing.lg, marginTop: Spacing.md, height: 46, flexDirection: "row" as const, alignItems: "center" as const, gap: Spacing.sm, paddingHorizontal: Spacing.md, borderRadius: Radius.sm, borderWidth: 1, borderColor: Colors.border }]) },
  searchInput: { flex: 1, color: Colors.text, fontSize: 14, writingDirection: "rtl" as const },
  govList: { gap: Spacing.sm, paddingHorizontal: Spacing.lg, paddingVertical: Spacing.sm },
  list: { padding: Spacing.lg, paddingBottom: Spacing["4xl"] },
  card: { flexDirection: "row-reverse", alignItems: "center", backgroundColor: Colors.surface, borderRadius: Radius.md, padding: Spacing.md, marginBottom: Spacing.sm, gap: Spacing.md, ...Shadow.soft },
  avatar: { width: 44, height: 44, borderRadius: 22, backgroundColor: Colors.primary, alignItems: "center", justifyContent: "center" },
  avatarText: { color: Colors.textInverse, fontSize: 17, fontWeight: "900" },
  cardCopy: { flex: 1, alignItems: "flex-end" },
  cardName: { color: Colors.text, ...Font.cardTitle },
  cardMeta: { color: Colors.textSecondary, ...Font.tiny, marginTop: Spacing.xs },
  cardRewards: { color: Colors.primary, ...Font.tiny, marginTop: Spacing.xs },
  empty: { textAlign: "center", color: Colors.textSecondary, marginTop: Spacing["4xl"], ...Font.caption },

  /* Detail */
  detailList: { padding: Spacing.lg, paddingBottom: Spacing["4xl"] },
  profileCard: { backgroundColor: Colors.black, borderRadius: Radius.lg, padding: Spacing.xl, flexDirection: "row-reverse", gap: Spacing.md, alignItems: "center", marginBottom: Spacing.lg, ...Shadow.raised },
  profileAvatar: { width: 52, height: 52, borderRadius: 26, backgroundColor: Colors.primary, alignItems: "center", justifyContent: "center" },
  profileInitial: { color: Colors.textInverse, fontSize: 22, fontWeight: "900" },
  profileCopy: { flex: 1, alignItems: "flex-end" },
  profileName: { color: Colors.textInverse, fontSize: 18, fontWeight: "900" },
  profileMeta: { color: "#A0A0A5", ...Font.small, marginTop: 2 },

  rewardSection: { backgroundColor: Colors.surface, borderRadius: Radius.md, padding: Spacing.lg, marginBottom: Spacing.md, ...Shadow.soft },
  sectionTitle: { color: Colors.text, ...Font.sectionTitle, textAlign: "right", marginBottom: Spacing.md },
  chipRow: { flexDirection: "row-reverse", flexWrap: "wrap", gap: Spacing.sm, marginBottom: Spacing.lg },
  chip: { borderRadius: Radius.sm, borderWidth: 1, borderColor: Colors.border, paddingHorizontal: Spacing.md, paddingVertical: Spacing.sm, backgroundColor: Colors.surface },
  chipActive: { backgroundColor: Colors.black, borderColor: Colors.black },
  chipText: { color: Colors.textSecondary, ...Font.chip },
  chipTextActive: { color: Colors.textInverse, fontWeight: "700" },
  twoFields: { flexDirection: "row-reverse", gap: Spacing.md },
  saveBtn: { height: 48, backgroundColor: Colors.primary, borderRadius: Radius.sm, alignItems: "center", justifyContent: "center", marginTop: Spacing.md },
  saveBtnText: { color: Colors.textInverse, ...Font.button },

  rewardCard: { flexDirection: "row-reverse", alignItems: "center", backgroundColor: Colors.surface, borderRadius: Radius.md, padding: Spacing.md, marginBottom: Spacing.sm, gap: Spacing.md, ...Shadow.soft },
  rewardCopy: { flex: 1, alignItems: "flex-end" },
  rewardTitle: { color: Colors.text, ...Font.cardTitle },
  rewardMeta: { color: Colors.textSecondary, ...Font.tiny, marginTop: Spacing.xs, textAlign: "right" },
});
