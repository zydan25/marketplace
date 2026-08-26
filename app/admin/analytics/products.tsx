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
  useProducts,
  toNumber,
  Colors,
  Font,
  Radius,
  Shadow,
  Spacing,
} from "@/components/admin";

type Tab = "overview" | "stock" | "ranking";

export default function ProductAnalytics() {
  const { data: products, loading } = useProducts();
  const [tab, setTab] = useState<Tab>("overview");

  const totalProducts = products.length;
  const publishedProducts = products.filter((p) => p.is_published).length;
  const outOfStock = products.filter((p) => p.stock === 0).length;
  const lowStock = products.filter((p) => p.stock > 0 && p.stock <= 5).length;
  const trendingProducts = products.filter((p) => p.is_trending).length;
  const totalSold = products.reduce((s, p) => s + p.sold_count, 0);
  const avgRating = products.filter((p) => toNumber(p.rating) > 0).length > 0
    ? products.reduce((s, p) => s + toNumber(p.rating), 0) / products.filter((p) => toNumber(p.rating) > 0).length
    : 0;

  /* ── Top selling products ───────────────────────── */

  const topSelling = useMemo(
    () =>
      [...products]
        .sort((a, b) => b.sold_count - a.sold_count)
        .slice(0, 10)
        .map((p) => ({ label: p.name, value: p.sold_count })),
    [products]
  );

  /* ── Top rated products ─────────────────────────── */

  const topRated = useMemo(
    () =>
      [...products]
        .filter((p) => toNumber(p.rating) > 0)
        .sort((a, b) => toNumber(b.rating) - toNumber(a.rating))
        .slice(0, 10)
        .map((p) => ({ label: p.name, value: toNumber(p.rating) })),
    [products]
  );

  /* ── Category distribution ──────────────────────── */

  const categoryDist = useMemo(() => {
    const cats: Record<string, number> = {};
    for (const p of products) {
      for (const c of p.categories ?? []) {
        cats[c.name || "غير مصنف"] = (cats[c.name || "غير مصنف"] || 0) + 1;
      }
    }
    const palette = [Colors.primary, Colors.info, Colors.success, Colors.warning, "#8B5CF6", "#EC4899", "#06B6D4"];
    return Object.entries(cats)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 7)
      .map(([label, value], i) => ({ label, value, color: palette[i % palette.length] }));
  }, [products]);

  /* ── Stock distribution ─────────────────────────── */

  const stockDist = useMemo(() => {
    const ranges = [
      { label: "نفد المخزون", count: 0, color: Colors.danger },
      { label: "1-5 قطع", count: 0, color: Colors.warning },
      { label: "6-20 قطعة", count: 0, color: Colors.info },
      { label: "21-50 قطعة", count: 0, color: Colors.success },
      { label: "أكثر من 50", count: 0, color: "#8B5CF6" },
    ];
    for (const p of products) {
      if (p.stock === 0) ranges[0].count++;
      else if (p.stock <= 5) ranges[1].count++;
      else if (p.stock <= 20) ranges[2].count++;
      else if (p.stock <= 50) ranges[3].count++;
      else ranges[4].count++;
    }
    return ranges.filter((r) => r.count > 0).map((r) => ({ label: r.label, value: r.count, color: r.color }));
  }, [products]);

  /* ── Low stock products ─────────────────────────── */

  const lowStockProducts = useMemo(
    () =>
      products
        .filter((p) => p.stock <= 5 && p.is_published)
        .sort((a, b) => a.stock - b.stock)
        .slice(0, 20),
    [products]
  );

  if (loading) {
    return (
      <AdminLayout title="تحليلات المنتجات">
        <ScrollView contentContainerStyle={styles.page}>
          <View style={styles.statsRow}><SkeletonStat /><SkeletonStat /></View>
          <View style={styles.statsRow}><SkeletonStat /><SkeletonStat /></View>
          <SkeletonCard />
        </ScrollView>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout title="تحليلات المنتجات">
      <ScrollView contentContainerStyle={styles.page} showsVerticalScrollIndicator={false}>
        <View style={styles.tabWrap}>
          <AdminTabs
            tabs={[
              { key: "overview", label: "نظرة عامة" },
              { key: "stock", label: "المخزون" },
              { key: "ranking", label: "الترتيب" },
            ]}
            active={tab}
            onChange={setTab}
          />
        </View>

        {/* Stats */}
        <View style={styles.statsRow}>
          <AdminStatTrend
            icon="inventory-2"
            iconColor={Colors.primary}
            iconBg={Colors.primaryLight}
            label="إجمالي المنتجات"
            value={totalProducts}
            trend={`${publishedProducts} منشورة`}
            trendDirection="up"
          />
          <AdminStatTrend
            icon="trending-up"
            iconColor={Colors.success}
            iconBg={Colors.successLight}
            label="المنتجات المباعة"
            value={totalSold}
            trend={`${trendingProducts} ترند`}
            trendDirection="up"
          />
        </View>

        <View style={styles.statsRow}>
          <AdminStatTrend
            icon="warning"
            iconColor={Colors.warning}
            iconBg={Colors.warningLight}
            label="مخزون منخفض"
            value={lowStock}
            trend={`${outOfStock} نفد`}
            trendDirection={lowStock > 0 ? "down" : "neutral"}
          />
          <AdminStatTrend
            icon="star"
            iconColor="#F59E0B"
            iconBg="#FFF8E8"
            label="متوسط التقييم"
            value={avgRating.toFixed(1)}
            trend={`${products.filter((p) => toNumber(p.rating) > 0).length} مقيّم`}
            trendDirection="neutral"
          />
        </View>

        {/* Charts */}
        {tab === "overview" && (
          <>
            {categoryDist.length > 0 && (
              <View style={styles.section}>
                <AdminPieChart data={categoryDist} title="المنتجات حسب الفئة" />
              </View>
            )}

            {topSelling.length > 0 && (
              <View style={styles.section}>
                <AdminBarChart
                  data={topSelling}
                  title="أكثر المنتجات مبيعاً"
                  formatValue={(v) => `${v} مبيعة`}
                />
              </View>
            )}
          </>
        )}

        {tab === "stock" && (
          <>
            {stockDist.length > 0 && (
              <View style={styles.section}>
                <AdminPieChart data={stockDist} title="توزيع المخزون" />
              </View>
            )}

            {lowStockProducts.length > 0 && (
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>⚠️ منتجات بمخزون منخفض</Text>
                <AdminDataTable
                  columns={[
                    { key: "name", label: "المنتج", width: 160 },
                    {
                      key: "stock",
                      label: "المخزون",
                      width: 80,
                      render: (p) => (
                        <Text style={[styles.cellBold, { color: p.stock === 0 ? Colors.danger : Colors.warning }]}>
                          {p.stock}
                        </Text>
                      ),
                    },
                    {
                      key: "sold_count",
                      label: "المباع",
                      width: 70,
                      render: (p) => <Text style={styles.cellText}>{p.sold_count}</Text>,
                    },
                  ]}
                  data={lowStockProducts}
                  emptyMessage="لا توجد منتجات بمخزون منخفض"
                  keyExtractor={(p) => String(p.id)}
                />
              </View>
            )}
          </>
        )}

        {tab === "ranking" && (
          <>
            {topSelling.length > 0 && (
              <View style={styles.section}>
                <AdminBarChart
                  data={topSelling}
                  title="أكثر المنتجات مبيعاً"
                  formatValue={(v) => `${v} مبيعة`}
                />
              </View>
            )}

            {topRated.length > 0 && (
              <View style={styles.section}>
                <AdminBarChart
                  data={topRated}
                  title="الأعلى تقييماً"
                  formatValue={(v) => `${v.toFixed(1)} ⭐`}
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
  sectionTitle: {
    color: Colors.text,
    ...Font.sectionTitle,
    textAlign: "right",
    marginBottom: Spacing.md,
  },
  cellText: {
    color: Colors.text,
    ...Font.small,
    textAlign: "right",
  },
  cellBold: {
    color: Colors.text,
    ...Font.chip,
    fontWeight: "700",
    textAlign: "right",
  },
});
