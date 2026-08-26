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
  toNumber,
  Colors,
  Radius,
  Shadow,
  Spacing,
} from "@/components/admin";

type Tab = "overview" | "products" | "status";

export default function ReferralAnalytics() {
  const { data: customers, loading } = useCustomers();
  const [tab, setTab] = useState<Tab>("overview");

  const totalCustomers = customers.length;
  const customersWithPoints = customers.filter((c) => toNumber(c.points_balance) > 0).length;
  const totalPoints = customers.reduce((s, c) => s + toNumber(c.points_balance), 0);
  const avgPoints = customersWithPoints > 0 ? Math.round(totalPoints / customersWithPoints) : 0;

  /* ── Points distribution ────────────────────────── */

  const pointsDist = useMemo(() => {
    const ranges = [
      { label: "لا نقاط", count: 0, color: Colors.textMuted },
      { label: "1-100", count: 0, color: Colors.info },
      { label: "101-500", count: 0, color: Colors.success },
      { label: "501-1000", count: 0, color: Colors.warning },
      { label: "1000+", count: 0, color: Colors.primary },
    ];
    for (const c of customers) {
      const pts = toNumber(c.points_balance);
      if (pts === 0) ranges[0].count++;
      else if (pts <= 100) ranges[1].count++;
      else if (pts <= 500) ranges[2].count++;
      else if (pts <= 1000) ranges[3].count++;
      else ranges[4].count++;
    }
    return ranges.filter((r) => r.count > 0).map((r) => ({ label: r.label, value: r.count, color: r.color }));
  }, [customers]);

  /* ── Top customers by points ────────────────────── */

  const topByPoints = useMemo(
    () =>
      customers
        .filter((c) => toNumber(c.points_balance) > 0)
        .sort((a, b) => toNumber(b.points_balance) - toNumber(a.points_balance))
        .slice(0, 10)
        .map((c) => ({
          label: c.name || c.phone,
          value: toNumber(c.points_balance),
        })),
    [customers]
  );

  if (loading) {
    return (
      <AdminLayout title="تحليلات الإحالات والمكافآت">
        <ScrollView contentContainerStyle={styles.page}>
          <View style={styles.statsRow}><SkeletonStat /><SkeletonStat /></View>
          <View style={styles.statsRow}><SkeletonStat /><SkeletonStat /></View>
          <SkeletonCard />
        </ScrollView>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout title="تحليلات الإحالات والمكافآت">
      <ScrollView contentContainerStyle={styles.page} showsVerticalScrollIndicator={false}>
        <View style={styles.tabWrap}>
          <AdminTabs
            tabs={[
              { key: "overview", label: "نظرة عامة" },
              { key: "products", label: "التوزيع" },
              { key: "status", label: "الترتيب" },
            ]}
            active={tab}
            onChange={setTab}
          />
        </View>

        {/* Stats */}
        <View style={styles.statsRow}>
          <AdminStatTrend
            icon="card-giftcard"
            iconColor={Colors.primary}
            iconBg={Colors.primaryLight}
            label="إجمالي النقاط"
            value={totalPoints.toLocaleString("ar-YE")}
            trend={`${customersWithPoints} عميل`}
            trendDirection="up"
          />
          <AdminStatTrend
            icon="stars"
            iconColor={Colors.success}
            iconBg={Colors.successLight}
            label="متوسط نقاط العميل"
            value={avgPoints.toLocaleString("ar-YE")}
            trend={`من ${customersWithPoints} عميل`}
            trendDirection="neutral"
          />
        </View>

        <View style={styles.statsRow}>
          <AdminStatTrend
            icon="people"
            iconColor={Colors.info}
            iconBg={Colors.infoLight}
            label="العملاء بنقاط"
            value={customersWithPoints}
            trend={`${totalCustomers - customersWithPoints} بدون نقاط`}
            trendDirection="neutral"
          />
          <AdminStatTrend
            icon="trending-up"
            iconColor="#8B5CF6"
            iconBg="#F3EEFF"
            label="أكبر رصيد"
            value={topByPoints.length > 0 ? topByPoints[0].value.toLocaleString("ar-YE") : "0"}
            trend={topByPoints.length > 0 ? topByPoints[0].label : "-"}
            trendDirection="neutral"
          />
        </View>

        {/* Charts */}
        {tab === "overview" && (
          <>
            {pointsDist.length > 0 && (
              <View style={styles.section}>
                <AdminPieChart data={pointsDist} title="توزيع النقاط بين العملاء" />
              </View>
            )}

            {topByPoints.length > 0 && (
              <View style={styles.section}>
                <AdminBarChart
                  data={topByPoints}
                  title="أكثر العملاء نقاطاً"
                  formatValue={(v) => `${v.toLocaleString("ar-YE")} نقطة`}
                />
              </View>
            )}
          </>
        )}

        {tab === "products" && pointsDist.length > 0 && (
          <View style={styles.section}>
            <AdminBarChart
              data={pointsDist}
              title="توزيع العملاء حسب النقاط"
              formatValue={(v) => `${v} عميل`}
            />
          </View>
        )}

        {tab === "status" && topByPoints.length > 0 && (
          <View style={styles.section}>
            <AdminBarChart
              data={topByPoints}
              title="أعلى 10 عملاء نقاطاً"
              formatValue={(v) => `${v.toLocaleString("ar-YE")} نقطة`}
            />
          </View>
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
