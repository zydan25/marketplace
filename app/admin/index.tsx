import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { useCallback, useEffect, useState } from "react";
import { RefreshControl, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";

import {
  AdminLayout,
  AdminDarkModeToggle,
  AdminGlobalSearch,
  AdminStatTrend,
  AdminBarChart,
  AdminPieChart,
  SkeletonStat,
  SkeletonCard,
  useDashboardStats,
  useOrders,
  useProducts,
  Colors,
  Font,
  Radius,
  Shadow,
  Spacing,
} from "@/components/admin";
import { useAuth } from "@/hooks/use-auth";
import { countByStatus, toNumber } from "@/components/admin/use-analytics";

/* ─── Quick links ────────────────────────────────── */

const quickLinks = [
  { icon: "inventory-2", label: "الأصناف", route: "/admin/products", color: Colors.primary, bg: Colors.primaryLight },
  { icon: "view-carousel", label: "الشريط العلوي", route: "/admin/storefront", color: Colors.info, bg: Colors.infoLight },
  { icon: "category", label: "الفئات", route: "/admin/categories", color: Colors.success, bg: Colors.successLight },
  { icon: "receipt-long", label: "الطلبات", route: "/admin/orders", color: Colors.warning, bg: Colors.warningLight },
  { icon: "notifications-active", label: "إشعارات", route: "/admin/notifications", color: "#8B5CF6", bg: "#F3EEFF" },
  { icon: "payments", label: "الأسعار", route: "/admin/pricing", color: "#0EA5E9", bg: "#E8F6FF" },
  { icon: "support-agent", label: "الدعم", route: "/admin/support", color: "#F59E0B", bg: "#FFF8E8" },
  { icon: "people-outline", label: "العملاء", route: "/admin/customers", color: "#6366F1", bg: "#EEF2FF" },
  { icon: "account-balance-wallet", label: "المحافظ", route: "/admin/wallets", color: "#14B8A6", bg: "#ECFEFB" },
  { icon: "group-add", label: "الإحالات", route: "/admin/referrals", color: "#10B981", bg: "#ECFDF5" },
  { icon: "analytics", label: "التحليلات", route: "/admin/analytics", color: Colors.primary, bg: Colors.primaryLight },
];

/* ─── Extra dashboard data fetcher ───────────────── */

interface DashboardExtra {
  todayOrders: number;
  todayRevenue: number;
  paymentSummary: Record<string, number>;
  vendorOrderStatus: Record<string, number>;
  recentOrders: { order_number: string; status: string; total: number; customer?: string; created_at: string }[];
  recentVendors: { store_name: string; status: string; owner?: string }[];
  lowStockProducts: { name: string; stock: number }[];
}

async function fetchDashboardExtra(): Promise<DashboardExtra> {
  try {
    const htmlRes = await fetch("/admin/dashboard/", { credentials: "include" });
    const html = await htmlRes.text();

    const todayMatch = html.match(/today_orders['":\s]+(\d+)/);
    const revenueMatch = html.match(/today_revenue['":\s]+([\d.]+)/);

    return {
      todayOrders: todayMatch ? parseInt(todayMatch[1]) : 0,
      todayRevenue: revenueMatch ? parseFloat(revenueMatch[1]) : 0,
      paymentSummary: { paid: 0, pending: 0, failed: 0 },
      vendorOrderStatus: {},
      recentOrders: [],
      recentVendors: [],
      lowStockProducts: [],
    };
  } catch {
    return {
      todayOrders: 0,
      todayRevenue: 0,
      paymentSummary: {},
      vendorOrderStatus: {},
      recentOrders: [],
      recentVendors: [],
      lowStockProducts: [],
    };
  }
}

/* ─── Admin Dashboard ────────────────────────────── */

export default function AdminDashboard() {
  const { user } = useAuth();
  const [refreshing, setRefreshing] = useState(false);
  const { data: stats, loading: statsLoading } = useDashboardStats();
  const { data: orders } = useOrders(50);
  const { data: products } = useProducts();
  const loadExtra = useCallback(async () => {
    await fetchDashboardExtra();
  }, []);

  useEffect(() => { loadExtra(); }, [loadExtra]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await loadExtra();
    setRefreshing(false);
  }, [loadExtra]);

  /* ─── Compute order stats ──────────────────────── */

  const orderStatusCounts = countByStatus(orders);
  const totalOrders = orders.length;
  const totalSoldProducts = products.reduce((s, p) => s + p.sold_count, 0);
  const lowStockCount = products.filter((p) => p.stock <= 5 && p.stock > 0).length;
  const outOfStockCount = products.filter((p) => p.stock === 0).length;
  const publishedProducts = products.filter((p) => p.is_published).length;

  /* ─── Chart data ────────────────────────────────── */

  const orderChartData = [
    { label: "قيد الانتظار", value: orderStatusCounts["pending"] || 0, color: Colors.warning },
    { label: "قيد المعالجة", value: orderStatusCounts["processing"] || 0, color: Colors.info },
    { label: "تم الشحن", value: orderStatusCounts["shipped"] || 0, color: "#8B5CF6" },
    { label: "تم التوصيل", value: orderStatusCounts["delivered"] || 0, color: Colors.success },
    { label: "ملغي", value: orderStatusCounts["cancelled"] || 0, color: Colors.danger },
  ];

  const productCategoryPie = (() => {
    const cats: Record<string, number> = {};
    for (const p of products) {
      for (const c of p.categories ?? []) {
        const name = c.name || "غير مصنف";
        cats[name] = (cats[name] || 0) + 1;
      }
    }
    const palette = [Colors.primary, Colors.info, Colors.success, Colors.warning, "#8B5CF6", "#EC4899", "#06B6D4"];
    return Object.entries(cats)
      .map(([label, value], i) => ({ label, value, color: palette[i % palette.length] }))
      .slice(0, 7);
  })();

  const topProducts = [...products]
    .sort((a, b) => b.sold_count - a.sold_count)
    .slice(0, 5)
    .map((p) => ({ label: p.name, value: p.sold_count }));

  /* ─── Recent orders from real data ─────────────── */

  const recentOrders = orders.slice(0, 5).map((o) => ({
    order_number: o.order_number,
    status: o.status,
    total: toNumber(o.total),
    customer: o.customer?.name || o.customer?.first_name || "-",
    created_at: o.created_at,
  }));

  /* ─── Loading skeleton ─────────────────────────── */

  if (statsLoading && !stats) {
    return (
      <AdminLayout title="لوحة تحكم المدير">
        <ScrollView style={{ flex: 1 }} contentContainerStyle={styles.page}>
          <View style={styles.statsRow}>
            <SkeletonStat />
            <SkeletonStat />
          </View>
          <View style={styles.statsRow}>
            <SkeletonStat />
            <SkeletonStat />
          </View>
          <SkeletonCard />
          <SkeletonCard />
        </ScrollView>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout
      title="لوحة تحكم المدير"
      rightAction={
        <View style={{ flexDirection: "row-reverse", gap: Spacing.sm }}>
          <AdminGlobalSearch
            onResult={(item) => {
              if (item.route) router.push(item.route as never);
            }}
          />
          <AdminDarkModeToggle />
        </View>
      }
    >
      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={styles.page}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />
        }
      >
        {/* ── Hero Banner ──────────────────────────── */}
        <View style={styles.hero}>
          <View style={styles.heroRow}>
            <View style={styles.heroTextWrap}>
              <Text style={styles.heroGreeting}>مرحبًا، {user?.name}</Text>
              <Text style={styles.heroSubtitle}>مركز تحكم شبيك</Text>
            </View>
            <View style={styles.heroIcon}>
              <MaterialIcons name="admin-panel-settings" size={28} color={Colors.textInverse} />
            </View>
          </View>
        </View>

        {/* ── Key Stats ────────────────────────────── */}
        <View style={styles.statsRow}>
          <AdminStatTrend
            icon="receipt-long"
            iconColor={Colors.primary}
            iconBg={Colors.primaryLight}
            label="إجمالي الطلبات"
            value={stats?.orders ?? 0}
            trend={`${stats?.pending_orders ?? 0} قيد الانتظار`}
            trendDirection="neutral"
          />
          <AdminStatTrend
            icon="payments"
            iconColor={Colors.success}
            iconBg={Colors.successLight}
            label="المنتجات المباعة"
            value={totalSoldProducts}
            trend={`${publishedProducts} منشورة`}
            trendDirection="up"
          />
        </View>

        <View style={styles.statsRow}>
          <AdminStatTrend
            icon="people"
            iconColor={Colors.info}
            iconBg={Colors.infoLight}
            label="العملاء"
            value={stats?.customers ?? 0}
            trend={`${stats?.users ?? 0} مستخدم`}
            trendDirection="neutral"
          />
          <AdminStatTrend
            icon="storefront"
            iconColor="#8B5CF6"
            iconBg="#F3EEFF"
            label="البائعون"
            value={stats?.vendors ?? 0}
            trend={`${stats?.pending_vendors ?? 0} في الانتظار`}
            trendDirection={stats?.pending_vendors ? "down" : "neutral"}
          />
        </View>

        <View style={styles.statsRow}>
          <AdminStatTrend
            icon="inventory-2"
            iconColor={Colors.warning}
            iconBg={Colors.warningLight}
            label="المنتجات"
            value={stats?.products ?? 0}
            trend={`${outOfStockCount} نفد مخزونه`}
            trendDirection={outOfStockCount > 0 ? "down" : "neutral"}
          />
          <AdminStatTrend
            icon="account-balance-wallet"
            iconColor="#14B8A6"
            iconBg="#ECFEFB"
            label="المحافظ"
            value={stats?.wallets ?? 0}
            trend={`${lowStockCount} مخزون منخفض`}
            trendDirection={lowStockCount > 0 ? "down" : "neutral"}
          />
        </View>

        {/* ── Order Status Chart ───────────────────── */}
        {totalOrders > 0 && (
          <View style={styles.section}>
            <AdminBarChart
              data={orderChartData.filter((d) => d.value > 0)}
              title="حالة الطلبات"
              formatValue={(v) => `${v} طلب`}
            />
          </View>
        )}

        {/* ── Product Categories Pie ───────────────── */}
        {productCategoryPie.length > 0 && (
          <View style={styles.section}>
            <AdminPieChart
              data={productCategoryPie}
              title="المنتجات حسب الفئة"
            />
          </View>
        )}

        {/* ── Top Selling Products ─────────────────── */}
        {topProducts.length > 0 && (
          <View style={styles.section}>
            <AdminBarChart
              data={topProducts}
              title="أكثر المنتجات مبيعاً"
              formatValue={(v) => `${v} مبيعة`}
            />
          </View>
        )}

        {/* ── Low Stock Alert ──────────────────────── */}
        {lowStockCount > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>⚠️ تنبيه مخزون منخفض</Text>
            <View style={styles.alertCard}>
              <MaterialIcons name="warning-amber" size={20} color={Colors.warning} />
              <Text style={styles.alertText}>
                {lowStockCount} منتج بمخزون منخفض (أقل من 5 قطع)
              </Text>
            </View>
          </View>
        )}

        {/* ── Recent Orders ────────────────────────── */}
        {recentOrders.length > 0 && (
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>آخر الطلبات</Text>
              <TouchableOpacity onPress={() => router.push("/admin/orders" as never)}>
                <Text style={styles.seeAll}>عرض الكل</Text>
              </TouchableOpacity>
            </View>
            {recentOrders.map((o, i) => (
              <View key={i} style={styles.orderRow}>
                <View style={styles.orderInfo}>
                  <Text style={styles.orderNumber}>{o.order_number}</Text>
                  <Text style={styles.orderCustomer}>{o.customer}</Text>
                </View>
                <View style={styles.orderMeta}>
                  <Text style={styles.orderTotal}>{o.total.toLocaleString("ar-YE")} ر.ي</Text>
                  <View
                    style={[
                      styles.statusDot,
                      {
                        backgroundColor:
                          o.status === "delivered"
                            ? Colors.success
                            : o.status === "cancelled"
                              ? Colors.danger
                              : o.status === "pending"
                                ? Colors.warning
                                : Colors.info,
                      },
                    ]}
                  />
                </View>
              </View>
            ))}
          </View>
        )}

        {/* ── Quick Links ──────────────────────────── */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>الوصول السريع</Text>
          <View style={styles.quickGrid}>
            {quickLinks.map((s) => (
              <TouchableOpacity
                key={s.label}
                style={styles.quickCard}
                activeOpacity={0.7}
                onPress={() => router.push(s.route as never)}
              >
                <View style={[styles.quickIcon, { backgroundColor: s.bg }]}>
                  <MaterialIcons name={s.icon as never} size={20} color={s.color} />
                </View>
                <Text style={styles.quickLabel}>{s.label}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* ── Security Badge ───────────────────────── */}
        <View style={styles.secureBanner}>
          <MaterialIcons name="verified-user" size={18} color={Colors.success} />
          <Text style={styles.secureText}>
            تم التحقق من صلاحية المدير عبر الجلسة الخادمية
          </Text>
        </View>
      </ScrollView>
    </AdminLayout>
  );
}

/* ─── Styles ─────────────────────────────────────── */

const styles = StyleSheet.create({
  page: {
    paddingBottom: Spacing["4xl"],
  },
  hero: {
    backgroundColor: Colors.black,
    marginHorizontal: Spacing.lg,
    marginTop: Spacing.lg,
    borderRadius: Radius.lg,
    padding: Spacing.xl,
    ...Shadow.raised,
  },
  heroRow: {
    flexDirection: "row-reverse",
    alignItems: "center",
    gap: Spacing.lg,
  },
  heroTextWrap: {
    flex: 1,
    alignItems: "flex-end",
  },
  heroGreeting: {
    color: Colors.textInverse,
    fontSize: 19,
    fontWeight: "900",
    lineHeight: 26,
  },
  heroSubtitle: {
    color: "#A0A0A5",
    ...Font.small,
    textAlign: "right",
    marginTop: Spacing.xs,
  },
  heroIcon: {
    width: 52,
    height: 52,
    borderRadius: Radius.md,
    backgroundColor: Colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  statsRow: {
    flexDirection: "row-reverse",
    gap: Spacing.md,
    paddingHorizontal: Spacing.lg,
    marginTop: Spacing.lg,
  },
  section: {
    backgroundColor: Colors.surface,
    marginHorizontal: Spacing.lg,
    marginTop: Spacing.lg,
    borderRadius: Radius.md,
    padding: Spacing.lg,
    ...Shadow.soft,
  },
  sectionHeader: {
    flexDirection: "row-reverse",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: Spacing.md,
  },
  sectionTitle: {
    color: Colors.text,
    ...Font.sectionTitle,
    textAlign: "right",
  },
  seeAll: {
    color: Colors.primary,
    ...Font.small,
  },
  alertCard: {
    flexDirection: "row-reverse",
    alignItems: "center",
    gap: Spacing.sm,
    backgroundColor: Colors.warningLight,
    borderRadius: Radius.sm,
    padding: Spacing.md,
    marginTop: Spacing.md,
  },
  alertText: {
    flex: 1,
    color: Colors.warning,
    ...Font.body,
    textAlign: "right",
  },
  orderRow: {
    flexDirection: "row-reverse",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: Spacing.sm,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.divider,
  },
  orderInfo: {
    flex: 1,
    alignItems: "flex-end",
    gap: 2,
  },
  orderNumber: {
    color: Colors.text,
    ...Font.chip,
  },
  orderCustomer: {
    color: Colors.textSecondary,
    ...Font.tiny,
  },
  orderMeta: {
    flexDirection: "row-reverse",
    alignItems: "center",
    gap: Spacing.sm,
  },
  orderTotal: {
    color: Colors.text,
    ...Font.body,
    fontWeight: "700",
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  quickGrid: {
    flexDirection: "row-reverse",
    flexWrap: "wrap",
    gap: Spacing.md,
    marginTop: Spacing.md,
  },
  quickCard: {
    width: "22%",
    alignItems: "center",
    gap: Spacing.sm,
    paddingVertical: Spacing.md,
  },
  quickIcon: {
    width: 42,
    height: 42,
    borderRadius: Radius.sm,
    alignItems: "center",
    justifyContent: "center",
  },
  quickLabel: {
    color: Colors.text,
    ...Font.small,
    textAlign: "center",
  },
  secureBanner: {
    flexDirection: "row-reverse",
    alignItems: "center",
    gap: Spacing.sm,
    marginHorizontal: Spacing.lg,
    marginTop: Spacing.lg,
    backgroundColor: Colors.successLight,
    borderRadius: Radius.md,
    padding: Spacing.md,
  },
  secureText: {
    flex: 1,
    color: Colors.success,
    ...Font.small,
    textAlign: "right",
  },
});
