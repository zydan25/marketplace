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
  useWallets,
  toNumber,
  formatDate,
  Colors,
  Font,
  Radius,
  Shadow,
  Spacing,
} from "@/components/admin";

type Tab = "overview" | "transactions" | "ranking";

export default function WalletAnalytics() {
  const { data: wallets, loading } = useWallets();
  const [tab, setTab] = useState<Tab>("overview");

  const totalBalance = wallets.reduce((s, w) => s + toNumber(w.balance), 0);
  const lockedWallets = wallets.filter((w) => w.is_locked).length;
  const activeWallets = wallets.length - lockedWallets;
  const avgBalance = wallets.length > 0 ? totalBalance / wallets.length : 0;

  /* ── All transactions ───────────────────────────── */

  const allTransactions = useMemo(() => {
    const txns: {
      id: number;
      wallet_id: number;
      user: string;
      transaction_type: string;
      amount: number;
      balance_after: number;
      reference: string;
      note: string;
      created_at: string;
    }[] = [];

    for (const w of wallets) {
      for (const t of w.transactions ?? []) {
        txns.push({
          id: t.id,
          wallet_id: w.id,
          user: w.user?.name || w.user?.phone || "-",
          transaction_type: t.transaction_type,
          amount: toNumber(t.amount),
          balance_after: toNumber(t.balance_after),
          reference: t.reference,
          note: t.note,
          created_at: t.created_at,
        });
      }
    }

    return txns.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [wallets]);

  /* ── Transaction type distribution ──────────────── */

  const typeDist = useMemo(() => {
    const types: Record<string, number> = {};
    for (const t of allTransactions) {
      types[t.transaction_type] = (types[t.transaction_type] || 0) + 1;
    }
    const labels: Record<string, string> = {
      top_up: "شحن",
      payment: "دفع",
      refund: "استرداد",
      reward: "مكافأة",
      withdrawal: "سحب",
      adjustment: "تعديل",
    };
    const palette = [Colors.success, Colors.info, Colors.warning, "#8B5CF6", Colors.danger, Colors.textMuted];
    return Object.entries(types)
      .sort(([, a], [, b]) => b - a)
      .map(([key, value], i) => ({
        label: labels[key] || key,
        value,
        color: palette[i % palette.length],
      }));
  }, [allTransactions]);

  /* ── Top wallets by balance ─────────────────────── */

  const topWallets = useMemo(
    () =>
      [...wallets]
        .sort((a, b) => toNumber(b.balance) - toNumber(a.balance))
        .slice(0, 10)
        .map((w) => ({
          label: w.user?.name || w.user?.phone || `محفظة #${w.id}`,
          value: Math.round(toNumber(w.balance)),
        })),
    [wallets]
  );

  /* ── Recent transactions ────────────────────────── */

  const recentTransactions = allTransactions.slice(0, 20);

  if (loading) {
    return (
      <AdminLayout title="تحليلات المحافظ">
        <ScrollView contentContainerStyle={styles.page}>
          <View style={styles.statsRow}><SkeletonStat /><SkeletonStat /></View>
          <View style={styles.statsRow}><SkeletonStat /><SkeletonStat /></View>
          <SkeletonCard />
        </ScrollView>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout title="تحليلات المحافظ">
      <ScrollView contentContainerStyle={styles.page} showsVerticalScrollIndicator={false}>
        <View style={styles.tabWrap}>
          <AdminTabs
            tabs={[
              { key: "overview", label: "نظرة عامة" },
              { key: "transactions", label: "المعاملات" },
              { key: "ranking", label: "الترتيب" },
            ]}
            active={tab}
            onChange={setTab}
          />
        </View>

        {/* Stats */}
        <View style={styles.statsRow}>
          <AdminStatTrend
            icon="account-balance-wallet"
            iconColor={Colors.success}
            iconBg={Colors.successLight}
            label="إجمالي الأرصدة"
            value={`${Math.round(totalBalance).toLocaleString("ar-YE")} ر.ي`}
            trend={`${wallets.length} محفظة`}
            trendDirection="up"
          />
          <AdminStatTrend
            icon="lock"
            iconColor={Colors.warning}
            iconBg={Colors.warningLight}
            label="المحافظ المقفلة"
            value={lockedWallets}
            trend={`${activeWallets} نشطة`}
            trendDirection={lockedWallets > 0 ? "down" : "neutral"}
          />
        </View>

        <View style={styles.statsRow}>
          <AdminStatTrend
            icon="trending-up"
            iconColor={Colors.info}
            iconBg={Colors.infoLight}
            label="متوسط الرصيد"
            value={`${Math.round(avgBalance).toLocaleString("ar-YE")} ر.ي`}
            trend={`من ${wallets.length} محفظة`}
            trendDirection="neutral"
          />
          <AdminStatTrend
            icon="receipt"
            iconColor="#8B5CF6"
            iconBg="#F3EEFF"
            label="إجمالي المعاملات"
            value={allTransactions.length}
            trend={`${typeDist.length} نوع`}
            trendDirection="neutral"
          />
        </View>

        {/* Charts */}
        {tab === "overview" && (
          <>
            {typeDist.length > 0 && (
              <View style={styles.section}>
                <AdminPieChart data={typeDist} title="أنواع المعاملات" />
              </View>
            )}

            {topWallets.length > 0 && (
              <View style={styles.section}>
                <AdminBarChart
                  data={topWallets}
                  title="أعلى المحافظ أرصدة"
                  formatValue={(v) => `${v.toLocaleString("ar-YE")} ر.ي`}
                />
              </View>
            )}
          </>
        )}

        {tab === "transactions" && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>آخر المعاملات ({allTransactions.length})</Text>
            <AdminDataTable
              columns={[
                {
                  key: "transaction_type",
                  label: "النوع",
                  width: 80,
                  render: (t: any) => (
                    <View style={[
                      styles.typeBadge,
                      {
                        backgroundColor:
                          t.transaction_type === "top_up"
                            ? `${Colors.success}18`
                            : t.transaction_type === "payment"
                              ? `${Colors.info}18`
                              : t.transaction_type === "refund"
                                ? `${Colors.warning}18`
                                : `${Colors.textMuted}18`,
                      },
                    ]}>
                      <Text style={[
                        styles.typeText,
                        {
                          color:
                            t.transaction_type === "top_up"
                              ? Colors.success
                              : t.transaction_type === "payment"
                                ? Colors.info
                                : t.transaction_type === "refund"
                                  ? Colors.warning
                                  : Colors.textMuted,
                        },
                      ]}>
                        {t.transaction_type === "top_up"
                          ? "شحن"
                          : t.transaction_type === "payment"
                            ? "دفع"
                            : t.transaction_type === "refund"
                              ? "استرداد"
                              : t.transaction_type === "reward"
                                ? "مكافأة"
                                : t.transaction_type === "withdrawal"
                                  ? "سحب"
                                  : "تعديل"}
                      </Text>
                    </View>
                  ),
                },
                {
                  key: "amount",
                  label: "المبلغ",
                  width: 100,
                  render: (t: any) => (
                    <Text style={[styles.cellBold, { color: t.amount >= 0 ? Colors.success : Colors.danger }]}>
                      {t.amount >= 0 ? "+" : ""}{t.amount.toLocaleString("ar-YE")} ر.ي
                    </Text>
                  ),
                },
                {
                  key: "user",
                  label: "المستخدم",
                  width: 120,
                  render: (t: any) => <Text style={styles.cellText}>{t.user}</Text>,
                },
                {
                  key: "created_at",
                  label: "التاريخ",
                  width: 110,
                  render: (t: any) => <Text style={styles.cellText}>{formatDate(t.created_at)}</Text>,
                },
              ]}
              data={recentTransactions}
              emptyMessage="لا توجد معاملات"
              keyExtractor={(t) => String(t.id)}
            />
          </View>
        )}

        {tab === "ranking" && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>ترتيب المحافظ حسب الرصيد</Text>
            <AdminDataTable
              columns={[
                {
                  key: "user",
                  label: "المستخدم",
                  width: 160,
                  render: (w: any) => <Text style={styles.cellText}>{w.user?.name || w.user?.phone || `-`}</Text>,
                },
                {
                  key: "balance",
                  label: "الرصيد",
                  width: 120,
                  render: (w: any) => (
                    <Text style={styles.cellBold}>{toNumber(w.balance).toLocaleString("ar-YE")} ر.ي</Text>
                  ),
                },
                {
                  key: "is_locked",
                  label: "الحالة",
                  width: 80,
                  render: (w: any) => (
                    <View style={[
                      styles.typeBadge,
                      { backgroundColor: w.is_locked ? `${Colors.danger}18` : `${Colors.success}18` },
                    ]}>
                      <Text style={[
                        styles.typeText,
                        { color: w.is_locked ? Colors.danger : Colors.success },
                      ]}>
                        {w.is_locked ? "مقفل" : "نشط"}
                      </Text>
                    </View>
                  ),
                },
              ]}
              data={[...wallets].sort((a, b) => toNumber(b.balance) - toNumber(a.balance))}
              emptyMessage="لا توجد محافظ"
              keyExtractor={(w) => String(w.id)}
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
  typeBadge: {
    paddingHorizontal: Spacing.sm,
    paddingVertical: 3,
    borderRadius: Radius.full,
    alignSelf: "flex-start",
  },
  typeText: {
    ...Font.tiny,
    fontWeight: "700",
  },
});
