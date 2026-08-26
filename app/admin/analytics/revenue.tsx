import { useState, useMemo } from "react";
import { ScrollView, StyleSheet, View } from "react-native";

import {
  AdminLayout,
  AdminStatTrend,
  AdminBarChart,
  AdminPieChart,
  AdminDateRange,
  AdminTabs,
  SkeletonCard,
  SkeletonStat,
  useOrders,
  useProducts,
  toNumber,
  sumField,
  Colors,
  Radius,
  Shadow,
  Spacing,
} from "@/components/admin";

type Tab = "overview" | "products" | "categories";

export default function RevenueAnalytics() {
  const { data: orders, loading: ordersLoading } = useOrders();
  const { data: products, loading: productsLoading } = useProducts();
  const [tab, setTab] = useState<Tab>("overview");
  const [preset, setPreset] = useState<"today" | "week" | "month" | "year" | "all">("all");

  const loading = ordersLoading || productsLoading;

  const filtered = useMemo(() => {
    if (preset === "all") return orders;
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const from = new Date(today);

    switch (preset) {
      case "today": break;
      case "week": from.setDate(from.getDate() - 6); break;
      case "month": from.setDate(from.getDate() - 29); break;
      case "year": from.setFullYear(from.getFullYear() - 1); break;
    }

    return orders.filter((o) => new Date(o.created_at) >= from);
  }, [orders, preset]);

  const paidOrders = filtered.filter((o) => o.payment_status === "paid");
  const totalRevenue = sumField(paidOrders, "total");
  const totalDiscounts = sumField(filtered, "discount");
  const totalShipping = sumField(filtered, "shipping_fee");
  const avgOrderValue = paidOrders.length > 0 ? totalRevenue / paidOrders.length : 0;

  /* ── Daily revenue for last 7 days ─────────────── */

  const dailyRevenue = useMemo(() => {
    const days: { label: string; value: number }[] = [];
    const now = new Date();
    for (let i = 6; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(d.getDate() - i);
      const dateStr = d.toISOString().split("T")[0];
      const dayLabel = `${d.getDate()}/${d.getMonth() + 1}`;
      const revenue = paidOrders
        .filter((o) => o.created_at.startsWith(dateStr))
        .reduce((s, o) => s + toNumber(o.total), 0);
      days.push({ label: dayLabel, value: Math.round(revenue) });
    }
    return days;
  }, [paidOrders]);

  /* ── Weekly revenue for last 4 weeks ───────────── */

  const weeklyRevenue = useMemo(() => {
    const weeks: { label: string; value: number }[] = [];
    const now = new Date();
    for (let i = 3; i >= 0; i--) {
      const weekStart = new Date(now);
      weekStart.setDate(weekStart.getDate() - (i * 7 + 6));
      const weekEnd = new Date(now);
      weekEnd.setDate(weekEnd.getDate() - i * 7);
      const revenue = paidOrders
        .filter((o) => {
          const d = new Date(o.created_at);
          return d >= weekStart && d <= weekEnd;
        })
        .reduce((s, o) => s + toNumber(o.total), 0);
      weeks.push({
        label: `الأسبوع ${4 - i}`,
        value: Math.round(revenue),
      });
    }
    return weeks;
  }, [paidOrders]);

  /* ── Top products by revenue ────────────────────── */

  const topProductsByRevenue = useMemo(() => {
    const productRevenue: Record<number, { name: string; revenue: number; count: number }> = {};

    for (const o of paidOrders) {
      for (const item of o.items ?? []) {
        const pid = item.product ?? 0;
        if (!productRevenue[pid]) {
          const product = products.find((p) => p.id === pid);
          productRevenue[pid] = {
            name: item.name_snapshot || product?.name || "منتج",
            revenue: 0,
            count: 0,
          };
        }
        productRevenue[pid].revenue += toNumber(item.vendor_total || item.unit_price) * (item.quantity || 1);
        productRevenue[pid].count += item.quantity || 1;
      }
    }

    return Object.values(productRevenue)
      .sort((a, b) => b.revenue - a.revenue)
      .slice(0, 10)
      .map((p) => ({ label: p.name, value: Math.round(p.revenue) }));
  }, [paidOrders, products]);

  /* ── Category revenue ───────────────────────────── */

  const categoryRevenue = useMemo(() => {
    const cats: Record<string, number> = {};
    for (const o of paidOrders) {
      for (const item of o.items ?? []) {
        const product = products.find((p) => p.id === item.product);
        for (const c of product?.categories ?? []) {
          const name = c.name || "غير مصنف";
          cats[name] = (cats[name] || 0) + toNumber(item.unit_price) * (item.quantity || 1);
        }
      }
    }
    const palette = [Colors.primary, Colors.info, Colors.success, Colors.warning, "#8B5CF6", "#EC4899", "#06B6D4"];
    return Object.entries(cats)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 7)
      .map(([label, value], i) => ({ label, value: Math.round(value), color: palette[i % palette.length] }));
  }, [paidOrders, products]);

  if (loading) {
    return (
      <AdminLayout title="تحليلات الإيرادات">
        <ScrollView contentContainerStyle={styles.page}>
          <View style={styles.statsRow}><SkeletonStat /><SkeletonStat /></View>
          <View style={styles.statsRow}><SkeletonStat /><SkeletonStat /></View>
          <SkeletonCard />
        </ScrollView>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout title="تحليلات الإيرادات">
      <ScrollView contentContainerStyle={styles.page} showsVerticalScrollIndicator={false}>
        {/* Tabs */}
        <View style={styles.tabWrap}>
          <AdminTabs
            tabs={[
              { key: "overview", label: "نظرة عامة" },
              { key: "products", label: "المنتجات" },
              { key: "categories", label: "الفئات" },
            ]}
            active={tab}
            onChange={setTab}
          />
        </View>

        {/* Date Range */}
        <View style={styles.filterWrap}>
          <AdminDateRange preset={preset} onPresetChange={setPreset} />
        </View>

        {/* Stats */}
        <View style={styles.statsRow}>
          <AdminStatTrend
            icon="payments"
            iconColor={Colors.success}
            iconBg={Colors.successLight}
            label="إجمالي الإيرادات"
            value={`${Math.round(totalRevenue).toLocaleString("ar-YE")} ر.ي`}
            trend={`${paidOrders.length} طلب مدفوع`}
            trendDirection="up"
          />
          <AdminStatTrend
            icon="shopping-cart"
            iconColor={Colors.info}
            iconBg={Colors.infoLight}
            label="متوسط قيمة الطلب"
            value={`${Math.round(avgOrderValue).toLocaleString("ar-YE")} ر.ي`}
            trend={`من ${paidOrders.length} طلب`}
            trendDirection="neutral"
          />
        </View>

        <View style={styles.statsRow}>
          <AdminStatTrend
            icon="local-shipping"
            iconColor={Colors.warning}
            iconBg={Colors.warningLight}
            label="رسوم التوصيل"
            value={`${Math.round(totalShipping).toLocaleString("ar-YE")} ر.ي`}
            trend={`${filtered.length} طلب`}
            trendDirection="neutral"
          />
          <AdminStatTrend
            icon="discount"
            iconColor="#8B5CF6"
            iconBg="#F3EEFF"
            label="الخصومات"
            value={`${Math.round(totalDiscounts).toLocaleString("ar-YE")} ر.ي`}
            trend={`${filtered.length} طلب`}
            trendDirection="down"
          />
        </View>

        {/* Charts */}
        {tab === "overview" && (
          <>
            {dailyRevenue.some((d) => d.value > 0) && (
              <View style={styles.section}>
                <AdminBarChart
                  data={dailyRevenue}
                  title="الإيرادات اليومية (آخر 7 أيام)"
                  formatValue={(v) => `${v.toLocaleString("ar-YE")} ر.ي`}
                />
              </View>
            )}

            {weeklyRevenue.some((d) => d.value > 0) && (
              <View style={styles.section}>
                <AdminBarChart
                  data={weeklyRevenue}
                  title="الإيرادات الأسبوعية (آخر 4 أسابيع)"
                  formatValue={(v) => `${v.toLocaleString("ar-YE")} ر.ي`}
                />
              </View>
            )}
          </>
        )}

        {tab === "products" && (
          <>
            {topProductsByRevenue.length > 0 && (
              <View style={styles.section}>
                <AdminBarChart
                  data={topProductsByRevenue}
                  title="أكثر المنتجات إيراداً"
                  formatValue={(v) => `${v.toLocaleString("ar-YE")} ر.ي`}
                />
              </View>
            )}

            {categoryRevenue.length > 0 && (
              <View style={styles.section}>
                <AdminPieChart data={categoryRevenue} title="الإيرادات حسب الفئة" />
              </View>
            )}
          </>
        )}

        {tab === "categories" && (
          <>
            {categoryRevenue.length > 0 && (
              <View style={styles.section}>
                <AdminBarChart
                  data={categoryRevenue}
                  title="الإيرادات حسب الفئة"
                  formatValue={(v) => `${v.toLocaleString("ar-YE")} ر.ي`}
                />
              </View>
            )}

            {categoryRevenue.length > 0 && (
              <View style={styles.section}>
                <AdminPieChart data={categoryRevenue} title="نسبة كل فئة" />
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
  filterWrap: {
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.md,
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
