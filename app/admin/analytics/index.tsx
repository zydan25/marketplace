import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";

import { AdminLayout, Colors, Font, Radius, Shadow, Spacing } from "@/components/admin";

const analyticsSections = [
  {
    icon: "receipt-long",
    label: "تحليلات الطلبات",
    description: "حالة الطلبات، الإيرادات، المتوسطات",
    route: "/admin/analytics/orders",
    color: Colors.primary,
    bg: Colors.primaryLight,
  },
  {
    icon: "payments",
    label: "تحليلات الإيرادات",
    description: "الإيرادات اليومية، الأسبوعية، حسب الفئة",
    route: "/admin/analytics/revenue",
    color: Colors.success,
    bg: Colors.successLight,
  },
  {
    icon: "inventory-2",
    label: "تحليلات المنتجات",
    description: "المخزون، التقييمات، الأكثر مبيعاً",
    route: "/admin/analytics/products",
    color: Colors.info,
    bg: Colors.infoLight,
  },
  {
    icon: "people",
    label: "تحليلات العملاء",
    description: "الجغرافيا، التكرار، الإنفاق",
    route: "/admin/analytics/customers",
    color: "#8B5CF6",
    bg: "#F3EEFF",
  },
  {
    icon: "storefront",
    label: "تحليلات البائعين",
    description: "الأداء، العمولات، الترتيب",
    route: "/admin/analytics/vendors",
    color: Colors.warning,
    bg: Colors.warningLight,
  },
  {
    icon: "account-balance-wallet",
    label: "تحليلات المحافظ",
    description: "الأرصدة، المعاملات، التوزيع",
    route: "/admin/analytics/wallets",
    color: "#14B8A6",
    bg: "#ECFEFB",
  },
  {
    icon: "card-giftcard",
    label: "تحليلات الإحالات",
    description: "النقاط، المكافآت، التوزيع",
    route: "/admin/analytics/referrals",
    color: "#10B981",
    bg: "#ECFDF5",
  },
  {
    icon: "support-agent",
    label: "تحليلات الدعم",
    description: "المحادثات، الرسائل، الحالة",
    route: "/admin/analytics/support",
    color: "#F59E0B",
    bg: "#FFF8E8",
  },
];

export default function AnalyticsIndex() {
  return (
    <AdminLayout title="التحليلات والإحصائيات">
      <View style={styles.page}>
        {/* Header */}
        <View style={styles.header}>
          <MaterialIcons name="analytics" size={32} color={Colors.primary} />
          <Text style={styles.headerTitle}>مركز التحليلات</Text>
          <Text style={styles.headerSubtitle}>
            تحليل شامل لكل جوانب المنصة
          </Text>
        </View>

        {/* Grid */}
        <View style={styles.grid}>
          {analyticsSections.map((s) => (
            <TouchableOpacity
              key={s.label}
              style={styles.card}
              activeOpacity={0.7}
              onPress={() => router.push(s.route as never)}
            >
              <View style={[styles.cardIcon, { backgroundColor: s.bg }]}>
                <MaterialIcons name={s.icon as never} size={24} color={s.color} />
              </View>
              <Text style={styles.cardLabel}>{s.label}</Text>
              <Text style={styles.cardText}>{s.description}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>
    </AdminLayout>
  );
}

const styles = StyleSheet.create({
  page: {
    flex: 1,
    paddingBottom: Spacing["4xl"],
  },
  header: {
    alignItems: "center",
    paddingVertical: Spacing["2xl"],
    paddingHorizontal: Spacing.lg,
    gap: Spacing.sm,
  },
  headerTitle: {
    color: Colors.text,
    fontSize: 20,
    fontWeight: "900",
    lineHeight: 28,
  },
  headerSubtitle: {
    color: Colors.textSecondary,
    ...Font.body,
    textAlign: "center",
  },
  grid: {
    flexDirection: "row-reverse",
    flexWrap: "wrap",
    gap: Spacing.md,
    padding: Spacing.lg,
  },
  card: {
    width: "47.5%",
    backgroundColor: Colors.surface,
    borderRadius: Radius.md,
    padding: Spacing.lg,
    alignItems: "flex-end",
    minHeight: 120,
    ...Shadow.soft,
  },
  cardIcon: {
    width: 46,
    height: 46,
    borderRadius: Radius.sm,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: Spacing.md,
  },
  cardLabel: {
    color: Colors.text,
    ...Font.cardTitle,
    textAlign: "right",
    marginBottom: Spacing.xs,
  },
  cardText: {
    color: Colors.textSecondary,
    ...Font.tiny,
    textAlign: "right",
    lineHeight: 16,
  },
});
