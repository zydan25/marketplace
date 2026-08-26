import { useState, useMemo } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";

import {
  AdminLayout,
  AdminStatTrend,
  AdminBarChart,
  AdminPieChart,
  AdminDataTable,
  AdminTabs,
  SkeletonCard,
  SkeletonStat,
  useVendors,
  useProducts,
  toNumber,
  Colors,
  Font,
  Radius,
  Shadow,
  Spacing,
} from "@/components/admin";

type Tab = "overview" | "performance" | "ranking";

export default function VendorAnalytics() {
  const { data: vendors, loading: vendorsLoading } = useVendors();
  const { data: products, loading: productsLoading } = useProducts();
  const [tab, setTab] = useState<Tab>("overview");

  const loading = vendorsLoading || productsLoading;

  const totalVendors = vendors.length;
  const activeVendors = vendors.filter((v) => v.status === "active").length;
  const pendingVendors = vendors.filter((v) => v.status === "pending").length;
  const suspendedVendors = vendors.filter((v) => v.status === "suspended").length;

  /* ── Vendor performance stats ───────────────────── */

  const vendorStats = useMemo(() => {
    const stats: Record<number, {
      store_name: string;
      orders: number;
      revenue: number;
      products: number;
      status: string;
    }> = {};

    for (const v of vendors) {
      stats[v.id] = {
        store_name: v.store_name,
        orders: 0,
        revenue: 0,
        products: 0,
        status: v.status,
      };
    }

    for (const p of products) {
      const vid = p.vendor?.id;
      if (vid && stats[vid]) {
        stats[vid].products++;
      }
    }

    return Object.values(stats);
  }, [vendors, products]);

  /* ── Status distribution ────────────────────────── */

  const statusPie = [
    { label: "نشط", value: activeVendors, color: Colors.success },
    { label: "معلق", value: pendingVendors, color: Colors.warning },
    { label: "موقوف", value: suspendedVendors, color: Colors.danger },
  ].filter((d) => d.value > 0);

  /* ── Top vendors by products ────────────────────── */

  const topByProducts = useMemo(
    () =>
      vendorStats
        .filter((v) => v.products > 0)
        .sort((a, b) => b.products - a.products)
        .slice(0, 10)
        .map((v) => ({ label: v.store_name, value: v.products })),
    [vendorStats]
  );

  /* ── Commission distribution ────────────────────── */

  const commissionDist = useMemo(() => {
    const ranges = [
      { label: "0-5%", count: 0 },
      { label: "5-10%", count: 0 },
      { label: "10-15%", count: 0 },
      { label: "15-20%", count: 0 },
      { label: "20%+", count: 0 },
    ];
    for (const v of vendors) {
      const pct = toNumber(v.commission_percent);
      if (pct <= 5) ranges[0].count++;
      else if (pct <= 10) ranges[1].count++;
      else if (pct <= 15) ranges[2].count++;
      else if (pct <= 20) ranges[3].count++;
      else ranges[4].count++;
    }
    return ranges.filter((r) => r.count > 0).map((r, i) => ({
      label: r.label,
      value: r.count,
      color: [Colors.success, Colors.info, Colors.primary, Colors.warning, Colors.danger][i],
    }));
  }, [vendors]);

  if (loading) {
    return (
      <AdminLayout title="تحليلات البائعين">
        <ScrollView contentContainerStyle={styles.page}>
          <View style={styles.statsRow}><SkeletonStat /><SkeletonStat /></View>
          <View style={styles.statsRow}><SkeletonStat /><SkeletonStat /></View>
          <SkeletonCard />
        </ScrollView>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout title="تحليلات البائعين">
      <ScrollView contentContainerStyle={styles.page} showsVerticalScrollIndicator={false}>
        <View style={styles.tabWrap}>
          <AdminTabs
            tabs={[
              { key: "overview", label: "نظرة عامة" },
              { key: "performance", label: "الأداء" },
              { key: "ranking", label: "الترتيب" },
            ]}
            active={tab}
            onChange={setTab}
          />
        </View>

        {/* Stats */}
        <View style={styles.statsRow}>
          <AdminStatTrend
            icon="storefront"
            iconColor={Colors.primary}
            iconBg={Colors.primaryLight}
            label="إجمالي البائعين"
            value={totalVendors}
            trend={`${activeVendors} نشط`}
            trendDirection="up"
          />
          <AdminStatTrend
            icon="hourglass-empty"
            iconColor={Colors.warning}
            iconBg={Colors.warningLight}
            label="بائعون معلقون"
            value={pendingVendors}
            trend={`${suspendedVendors} موقوف`}
            trendDirection={pendingVendors > 0 ? "down" : "neutral"}
          />
        </View>

        <View style={styles.statsRow}>
          <AdminStatTrend
            icon="check-circle"
            iconColor={Colors.success}
            iconBg={Colors.successLight}
            label="البائعون النشطون"
            value={activeVendors}
            trend={`${totalVendors > 0 ? Math.round((activeVendors / totalVendors) * 100) : 0}%`}
            trendDirection="up"
          />
          <AdminStatTrend
            icon="block"
            iconColor={Colors.danger}
            iconBg={Colors.dangerLight}
            label="البائعون الموقوفون"
            value={suspendedVendors}
            trend={suspendedVendors > 0 ? "يحتاج مراجعة" : "لا يوجد"}
            trendDirection={suspendedVendors > 0 ? "down" : "neutral"}
          />
        </View>

        {/* Charts */}
        {tab === "overview" && (
          <>
            {statusPie.length > 0 && (
              <View style={styles.section}>
                <AdminPieChart data={statusPie} title="حالة البائعين" />
              </View>
            )}

            {topByProducts.length > 0 && (
              <View style={styles.section}>
                <AdminBarChart
                  data={topByProducts}
                  title="أكثر البائعين منتجاتاً"
                  formatValue={(v) => `${v} منتج`}
                />
              </View>
            )}
          </>
        )}

        {tab === "performance" && (
          <>
            {commissionDist.length > 0 && (
              <View style={styles.section}>
                <AdminPieChart data={commissionDist} title="توزيع العمولات" />
              </View>
            )}

            {topByProducts.length > 0 && (
              <View style={styles.section}>
                <AdminBarChart
                  data={topByProducts}
                  title="البائعون حسب عدد المنتجات"
                  formatValue={(v) => `${v} منتج`}
                />
              </View>
            )}
          </>
        )}

        {tab === "ranking" && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>ترتيب البائعين</Text>
            <AdminDataTable
              columns={[
                { key: "store_name", label: "المتجر", width: 160 },
                {
                  key: "status",
                  label: "الحالة",
                  width: 80,
                  render: (v: any) => (
                    <View style={[
                      styles.statusBadge,
                      {
                        backgroundColor:
                          v.status === "active"
                            ? `${Colors.success}18`
                            : v.status === "pending"
                              ? `${Colors.warning}18`
                              : `${Colors.danger}18`,
                      },
                    ]}>
                      <Text style={[
                        styles.statusText,
                        {
                          color:
                            v.status === "active"
                              ? Colors.success
                              : v.status === "pending"
                                ? Colors.warning
                                : Colors.danger,
                        },
                      ]}>
                        {v.status === "active" ? "نشط" : v.status === "pending" ? "معلق" : "موقوف"}
                      </Text>
                    </View>
                  ),
                },
                {
                  key: "products",
                  label: "المنتجات",
                  width: 80,
                  render: (v: any) => <Text style={styles.cellBold}>{vendorStats.find((vs) => vs.store_name === v.store_name)?.products ?? 0}</Text>,
                },
              ]}
              data={vendors}
              emptyMessage="لا يوجد بائعون"
              keyExtractor={(v) => String(v.id)}
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
  sectionTitle: {
    color: Colors.text,
    ...Font.sectionTitle,
    textAlign: "right",
    marginBottom: Spacing.md,
  },
  cellBold: {
    color: Colors.text,
    ...Font.chip,
    fontWeight: "700",
    textAlign: "right",
  },
  statusBadge: {
    paddingHorizontal: Spacing.sm,
    paddingVertical: 3,
    borderRadius: Radius.full,
    alignSelf: "flex-start",
  },
  statusText: {
    ...Font.tiny,
    fontWeight: "700",
  },
});
