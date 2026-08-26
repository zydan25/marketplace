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
  useConversations,
  formatDate,
  Colors,
  Font,
  Radius,
  Shadow,
  Spacing,
} from "@/components/admin";

type Tab = "overview" | "status" | "details";

export default function SupportAnalytics() {
  const { data: conversations, loading } = useConversations();
  const [tab, setTab] = useState<Tab>("overview");

  const totalConversations = conversations.length;
  const openConversations = conversations.filter((c) => !c.is_closed).length;
  const closedConversations = conversations.filter((c) => c.is_closed).length;

  /* ── Message stats ──────────────────────────────── */

  const totalMessages = conversations.reduce((s, c) => s + (c.messages?.length || 0), 0);
  const unreadMessages = conversations.reduce(
    (s, c) => s + (c.messages?.filter((m) => !m.is_read).length || 0),
    0
  );
  const avgMessagesPerConversation = totalConversations > 0 ? Math.round(totalMessages / totalConversations) : 0;

  /* ── Status distribution ────────────────────────── */

  const statusPie = [
    { label: "مفتوحة", value: openConversations, color: Colors.warning },
    { label: "مغلقة", value: closedConversations, color: Colors.success },
  ].filter((d) => d.value > 0);

  /* ── Messages per conversation ──────────────────── */

  const messagesPerConvo = useMemo(
    () =>
      conversations
        .sort((a, b) => (b.messages?.length || 0) - (a.messages?.length || 0))
        .slice(0, 10)
        .map((c) => ({
          label: c.subject || `محادثة #${c.id}`,
          value: c.messages?.length || 0,
        })),
    [conversations]
  );

  if (loading) {
    return (
      <AdminLayout title="تحليلات الدعم">
        <ScrollView contentContainerStyle={styles.page}>
          <View style={styles.statsRow}><SkeletonStat /><SkeletonStat /></View>
          <View style={styles.statsRow}><SkeletonStat /><SkeletonStat /></View>
          <SkeletonCard />
        </ScrollView>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout title="تحليلات الدعم">
      <ScrollView contentContainerStyle={styles.page} showsVerticalScrollIndicator={false}>
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

        {/* Stats */}
        <View style={styles.statsRow}>
          <AdminStatTrend
            icon="support-agent"
            iconColor={Colors.primary}
            iconBg={Colors.primaryLight}
            label="إجمالي المحادثات"
            value={totalConversations}
            trend={`${openConversations} مفتوحة`}
            trendDirection={openConversations > 0 ? "down" : "neutral"}
          />
          <AdminStatTrend
            icon="chat"
            iconColor={Colors.info}
            iconBg={Colors.infoLight}
            label="إجمالي الرسائل"
            value={totalMessages}
            trend={`${unreadMessages} غير مقروءة`}
            trendDirection={unreadMessages > 0 ? "down" : "neutral"}
          />
        </View>

        <View style={styles.statsRow}>
          <AdminStatTrend
            icon="mark-chat-read"
            iconColor={Colors.success}
            iconBg={Colors.successLight}
            label="المحادثات المغلقة"
            value={closedConversations}
            trend={`${totalConversations > 0 ? Math.round((closedConversations / totalConversations) * 100) : 0}%`}
            trendDirection="up"
          />
          <AdminStatTrend
            icon="functions"
            iconColor="#8B5CF6"
            iconBg="#F3EEFF"
            label="متوسط الرسائل/محادثة"
            value={avgMessagesPerConversation}
            trend={`${totalConversations} محادثة`}
            trendDirection="neutral"
          />
        </View>

        {/* Charts */}
        {tab === "overview" && (
          <>
            {statusPie.length > 0 && (
              <View style={styles.section}>
                <AdminPieChart data={statusPie} title="حالة المحادثات" />
              </View>
            )}

            {messagesPerConvo.length > 0 && (
              <View style={styles.section}>
                <AdminBarChart
                  data={messagesPerConvo}
                  title="المحادثات حسب عدد الرسائل"
                  formatValue={(v) => `${v} رسالة`}
                />
              </View>
            )}
          </>
        )}

        {tab === "status" && (
          <View style={styles.section}>
            <AdminBarChart
              data={[
                { label: "مفتوحة", value: openConversations, color: Colors.warning },
                { label: "مغلقة", value: closedConversations, color: Colors.success },
              ].filter((d) => d.value > 0)}
              title="المحادثات حسب الحالة"
              formatValue={(v) => `${v} محادثة`}
            />
          </View>
        )}

        {tab === "details" && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>المحادثات ({totalConversations})</Text>
            <AdminDataTable
              columns={[
                { key: "subject", label: "الموضوع", width: 160 },
                {
                  key: "is_closed",
                  label: "الحالة",
                  width: 80,
                  render: (c: any) => (
                    <View style={[
                      styles.statusBadge,
                      { backgroundColor: c.is_closed ? `${Colors.success}18` : `${Colors.warning}18` },
                    ]}>
                      <Text style={[
                        styles.statusText,
                        { color: c.is_closed ? Colors.success : Colors.warning },
                      ]}>
                        {c.is_closed ? "مغلقة" : "مفتوحة"}
                      </Text>
                    </View>
                  ),
                },
                {
                  key: "messages",
                  label: "الرسائل",
                  width: 70,
                  render: (c: any) => (
                    <Text style={styles.cellBold}>{c.messages?.length || 0}</Text>
                  ),
                },
                {
                  key: "created_at",
                  label: "التاريخ",
                  width: 110,
                  render: (c: any) => <Text style={styles.cellText}>{formatDate(c.created_at)}</Text>,
                },
              ]}
              data={conversations}
              emptyMessage="لا توجد محادثات"
              keyExtractor={(c) => String(c.id)}
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
