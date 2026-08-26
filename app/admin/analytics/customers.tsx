import { useState, useMemo } from "react";
import { ScrollView, StyleSheet, View } from "react-native";

import {
  AdminLayout,
  AdminStatTrend,
  AdminBarChart,
  AdminPieChart,
  AdminTabs,
  SkeletonCard,
  SkeletonStat,
  useCustomers,
  useOrders,
  getGovernorateCounts,
  toNumber,
  Colors,
  Radius,
  Shadow,
  Spacing,
} from "@/components/admin";

type Tab = "overview" | "geography" | "ranking";

export default function CustomerAnalytics() {
  const { data: customers, loading: customersLoading } = useCustomers();
  const { data: orders, loading: ordersLoading } = useOrders();
  const [tab, setTab] = useState<Tab>("overview");

  const loading = customersLoading || ordersLoading;

  const totalCustomers = customers.length;
  const activeCustomers = customers.filter((c) => c.is_active).length;
  const inactiveCustomers = totalCustomers - activeCustomers;

  /* ── Customer order stats ───────────────────────── */

  const customerOrderStats = useMemo(() => {
    const stats: Record<number, { name: string; orders: number; totalSpent: number }> = {};
    for (const o of orders) {
      const cid = o.customer?.id ?? 0;
      if (!cid) continue;
      if (!stats[cid]) {
        stats[cid] = {
          name: o.customer?.name || o.customer?.first_name || "عميل",
          orders: 0,
          totalSpent: 0,
        };
      }
      stats[cid].orders++;
      if (o.payment_status === "paid") {
        stats[cid].totalSpent += toNumber(o.total);
      }
    }
    return Object.values(stats);
  }, [orders]);

  const customersWithOrders = customerOrderStats.length;
  const repeatCustomers = customerOrderStats.filter((c) => c.orders > 1).length;
  const avgOrdersPerCustomer = customersWithOrders > 0 ? orders.length / customersWithOrders : 0;
  const topSpender = customerOrderStats.sort((a, b) => b.totalSpent - a.totalSpent)[0];

  /* ── Governorate distribution ───────────────────── */

  const governorateData = useMemo(() => {
    const counts = getGovernorateCounts(customers);
    return Object.entries(counts)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 10)
      .map(([label, value]) => ({ label, value }));
  }, [customers]);

  /* ── Active vs inactive ─────────────────────────── */

  const activityPie = [
    { label: "نشط", value: activeCustomers, color: Colors.success },
    { label: "غير نشط", value: inactiveCustomers, color: Colors.textMuted },
  ].filter((d) => d.value > 0);

  /* ── Top customers ──────────────────────────────── */

  const topCustomers = useMemo(
    () =>
      customerOrderStats
        .sort((a, b) => b.orders - a.orders)
        .slice(0, 10)
        .map((c) => ({ label: c.name, value: c.orders })),
    [customerOrderStats]
  );

  const topSpenders = useMemo(
    () =>
      customerOrderStats
        .filter((c) => c.totalSpent > 0)
        .sort((a, b) => b.totalSpent - a.totalSpent)
        .slice(0, 10)
        .map((c) => ({ label: c.name, value: Math.round(c.totalSpent) })),
    [customerOrderStats]
  );

  if (loading) {
    return (
      <AdminLayout title="تحليلات العملاء">
        <ScrollView contentContainerStyle={styles.page}>
          <View style={styles.statsRow}><SkeletonStat /><SkeletonStat /></View>
          <View style={styles.statsRow}><SkeletonStat /><SkeletonStat /></View>
          <SkeletonCard />
        </ScrollView>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout title="تحليلات العملاء">
      <ScrollView contentContainerStyle={styles.page} showsVerticalScrollIndicator={false}>
        <View style={styles.tabWrap}>
          <AdminTabs
            tabs={[
              { key: "overview", label: "نظرة عامة" },
              { key: "geography", label: "الجغرافيا" },
              { key: "ranking", label: "الترتيب" },
            ]}
            active={tab}
            onChange={setTab}
          />
        </View>

        {/* Stats */}
        <View style={styles.statsRow}>
          <AdminStatTrend
            icon="people"
            iconColor={Colors.info}
            iconBg={Colors.infoLight}
            label="إجمالي العملاء"
            value={totalCustomers}
            trend={`${customersWithOrders} طلبوا`}
            trendDirection="up"
          />
          <AdminStatTrend
            icon="person"
            iconColor={Colors.success}
            iconBg={Colors.successLight}
            label="العملاء النشطون"
            value={activeCustomers}
            trend={`${inactiveCustomers} غير نشط`}
            trendDirection={inactiveCustomers > 0 ? "down" : "neutral"}
          />
        </View>

        <View style={styles.statsRow}>
          <AdminStatTrend
            icon="repeat"
            iconColor="#8B5CF6"
            iconBg="#F3EEFF"
            label="العملاء المتكررون"
            value={repeatCustomers}
            trend={`${Math.round(avgOrdersPerCustomer * 10) / 10} طلب/عميل`}
            trendDirection="neutral"
          />
          <AdminStatTrend
            icon="account-balance-wallet"
            iconColor={Colors.warning}
            iconBg={Colors.warningLight}
            label="أكبر عميل"
            value={topSpender ? `${Math.round(topSpender.totalSpent).toLocaleString("ar-YE")} ر.ي` : "0 ر.ي"}
            trend={topSpender?.name}
            trendDirection="neutral"
          />
        </View>

        {/* Charts */}
        {tab === "overview" && (
          <>
            {activityPie.length > 0 && (
              <View style={styles.section}>
                <AdminPieChart data={activityPie} title="العملاء النشطون وغير النشطون" />
              </View>
            )}

            {topCustomers.length > 0 && (
              <View style={styles.section}>
                <AdminBarChart
                  data={topCustomers}
                  title="أكثر العملاء طلباتاً"
                  formatValue={(v) => `${v} طلب`}
                />
              </View>
            )}
          </>
        )}

        {tab === "geography" && (
          <>
            {governorateData.length > 0 && (
              <View style={styles.section}>
                <AdminBarChart
                  data={governorateData}
                  title="العملاء حسب المحافظة"
                  formatValue={(v) => `${v} عميل`}
                />
              </View>
            )}
          </>
        )}

        {tab === "ranking" && (
          <>
            {topCustomers.length > 0 && (
              <View style={styles.section}>
                <AdminBarChart
                  data={topCustomers}
                  title="أكثر العملاء طلباتاً"
                  formatValue={(v) => `${v} طلب`}
                />
              </View>
            )}

            {topSpenders.length > 0 && (
              <View style={styles.section}>
                <AdminBarChart
                  data={topSpenders}
                  title="أكثر العملاء إنفاقاً"
                  formatValue={(v) => `${v.toLocaleString("ar-YE")} ر.ي`}
                />
              </View>
            )}
          </>
        )}
      </ScrollView>
    </AdminLayout>
  );
}

const styles = StyleSheet.create({
  page: {
    paddingBottom: Spacing["4xl"],
  },
  tabWrap: {
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.lg,
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
});
