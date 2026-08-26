import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { useState, useMemo } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";

import {
  AdminLayout,
  AdminStatTrend,
  AdminBarChart,
  AdminPieChart,
  AdminDataTable,
  AdminDateRange,
  AdminTabs,
  SkeletonCard,
  SkeletonStat,
  useOrders,
  countByStatus,
  toNumber,
  sumField,
  formatDate,
  exportToCSV,
  Colors,
  Font,
  Radius,
  Shadow,
  Spacing,
} from "@/components/admin";

type Tab = "overview" | "status" | "details";

const STATUS_LABELS: Record<string, string> = {
  pending: "قيد الانتظار",
  confirmed: "مؤكد",
  processing: "قيد المعالجة",
  shipped: "تم الشحن",
  partially_fulfilled: "مسلّم جزئياً",
  delivered: "تم التوصيل",
  cancelled: "ملغي",
  refunded: "مسترجع",
};

const STATUS_COLORS: Record<string, string> = {
  pending: "#E97B11",
  confirmed: "#007AFF",
  processing: "#8B5CF6",
  shipped: "#06B6D4",
  partially_fulfilled: "#F59E0B",
  delivered: "#168451",
  cancelled: "#E60023",
  refunded: "#6C6C70",
};

export default function OrderAnalytics() {
  const { data: orders, loading } = useOrders();
  const [tab, setTab] = useState<Tab>("overview");
  const [preset, setPreset] = useState<"today" | "week" | "month" | "year" | "all">("all");

  const filtered = useMemo(() => {
    if (preset === "all") return orders;
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const from = new Date(today);

    if (preset === "week") from.setDate(from.getDate() - 6);
    else if (preset === "month") from.setDate(from.getDate() - 29);
    else if (preset === "year") from.setFullYear(from.getFullYear() - 1);

    return orders.filter((o) => {
      const d = new Date(o.created_at);
      return d >= from;
    });
  }, [orders, preset]);

  const statusCounts = countByStatus(filtered);
  const totalRevenue = sumField(
    filtered.filter((o) => o.payment_status === "paid"),
    "total"
  );
  const avgOrderValue = filtered.length > 0 ? totalRevenue / filtered.filter((o) => o.payment_status === "paid").length : 0;

  const paymentCounts = countByStatus(filtered.map((o) => ({ status: o.payment_status })));

  const statusChartData = Object.entries(statusCounts)
    .map(([key, val]) => ({
      label: STATUS_LABELS[key] || key,
      value: val,
      color: STATUS_COLORS[key] || Colors.textMuted,
    }))
    .filter((d) => d.value > 0);

  const paymentPieData = [
    { label: "مدفوع", value: paymentCounts["paid"] || 0, color: Colors.success },
    { label: "معلق", value: paymentCounts["pending"] || 0, color: Colors.warning },
    { label: "فاشل", value: paymentCounts["failed"] || 0, color: Colors.danger },
    { label: "مسترجع", value: paymentCounts["refunded"] || 0, color: Colors.textMuted },
  ].filter((d) => d.value > 0);

  const handleExport = () => {
    exportToCSV({
      filename: `orders-analytics-${new Date().toISOString().split("T")[0]}`,
      headers: ["رقم الطلب", "العميل", "الحالة", "الإجمالي", "حالة الدفع", "التاريخ"],
      rows: filtered.map((o) => [
        o.order_number,
        o.customer?.name || o.customer?.first_name || "-",
        STATUS_LABELS[o.status] || o.status,
        toNumber(o.total),
        o.payment_status,
        formatDate(o.created_at),
      ]),
    });
  };

  if (loading) {
    return (
      <AdminLayout title="تحليلات الطلبات">
        <ScrollView contentContainerStyle={styles.page}>
          <View style={styles.statsRow}><SkeletonStat /><SkeletonStat /></View>
          <View style={styles.statsRow}><SkeletonStat /><SkeletonStat /></View>
          <SkeletonCard />
        </ScrollView>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout
      title="تحليلات الطلبات"
      rightAction={
        <MaterialIcons
          name="file-download"
          size={22}
          color={Colors.primary}
          onPress={handleExport}
          style={{ padding: Spacing.sm }}
        />
      }
    >
      <ScrollView contentContainerStyle={styles.page} showsVerticalScrollIndicator={false}>
        {/* Tabs */}
        <View style={styles.tabWrap}>
          <AdminTabs
            tabs={[
              { key: "overview", label: "نظرة عامة" },
              { key: "status", label: "الحالة" },
              { key: "details", label: "التفاصيل" },
            ]}
            active={tab}
            onChange={setTab}
          />
        </View>

        {/* Date Range */}
        <View style={styles.filterWrap}>
          <AdminDateRange
            preset={preset}
            onPresetChange={setPreset}
          />
        </View>

        {/* Stats */}
        <View style={styles.statsRow}>
          <AdminStatTrend
            icon="receipt-long"
            iconColor={Colors.primary}
            iconBg={Colors.primaryLight}
            label="إجمالي الطلبات"
            value={filtered.length}
            trend={`${filtered.filter((o) => o.status === "pending").length} قيد الانتظار`}
            trendDirection={filtered.filter((o) => o.status === "pending").length > 0 ? "down" : "neutral"}
          />
          <AdminStatTrend
            icon="payments"
            iconColor={Colors.success}
            iconBg={Colors.successLight}
            label="إجمالي الإيرادات"
            value={`${Math.round(totalRevenue).toLocaleString("ar-YE")} ر.ي`}
            trend={`${filtered.filter((o) => o.payment_status === "paid").length} مدفوعة`}
            trendDirection="up"
          />
        </View>

        <View style={styles.statsRow}>
          <AdminStatTrend
            icon="shopping-cart"
            iconColor={Colors.info}
            iconBg={Colors.infoLight}
            label="متوسط قيمة الطلب"
            value={`${Math.round(avgOrderValue).toLocaleString("ar-YE")} ر.ي`}
            trend={`من ${filtered.filter((o) => o.payment_status === "paid").length} طلب`}
            trendDirection="neutral"
          />
          <AdminStatTrend
            icon="cancel"
            iconColor={Colors.danger}
            iconBg={Colors.dangerLight}
            label="الطلبات الملغاة"
            value={statusCounts["cancelled"] || 0}
            trend={filtered.length > 0 ? `${Math.round(((statusCounts["cancelled"] || 0) / filtered.length) * 100)}%` : "0%"}
            trendDirection="down"
          />
        </View>

        {/* Charts */}
        {tab === "overview" && (
          <>
            {statusChartData.length > 0 && (
              <View style={styles.section}>
                <AdminBarChart
                  data={statusChartData}
                  title="توزيع الطلبات حسب الحالة"
                  formatValue={(v) => `${v} طلب`}
                />
              </View>
            )}

            {paymentPieData.length > 0 && (
              <View style={styles.section}>
                <AdminPieChart data={paymentPieData} title="حالة الدفع" />
              </View>
            )}
          </>
        )}

        {tab === "status" && (
          <View style={styles.section}>
            <AdminBarChart
              data={statusChartData}
              title="الطلبات حسب الحالة"
              formatValue={(v) => `${v} طلب`}
            />
          </View>
        )}

        {tab === "details" && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>الطلبات المفلترة ({filtered.length})</Text>
            <AdminDataTable
              columns={[
                { key: "order_number", label: "رقم الطلب", width: 110 },
                {
                  key: "customer",
                  label: "العميل",
                  width: 120,
                  render: (o) => (
                    <Text style={styles.cellText}>
                      {o.customer?.name || o.customer?.first_name || "-"}
                    </Text>
                  ),
                },
                {
                  key: "status",
                  label: "الحالة",
                  width: 100,
                  render: (o) => (
                    <View style={[styles.statusBadge, { backgroundColor: `${STATUS_COLORS[o.status] || Colors.textMuted}18` }]}>
                      <Text style={[styles.statusText, { color: STATUS_COLORS[o.status] || Colors.textMuted }]}>
                        {STATUS_LABELS[o.status] || o.status}
                      </Text>
                    </View>
                  ),
                },
                {
                  key: "total",
                  label: "الإجمالي",
                  width: 100,
                  render: (o) => (
                    <Text style={styles.cellBold}>{toNumber(o.total).toLocaleString("ar-YE")} ر.ي</Text>
                  ),
                },
                {
                  key: "created_at",
                  label: "التاريخ",
                  width: 110,
                  render: (o) => <Text style={styles.cellText}>{formatDate(o.created_at)}</Text>,
                },
              ]}
              data={filtered}
              emptyMessage="لا توجد طلبات"
              keyExtractor={(o) => String(o.id)}
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
