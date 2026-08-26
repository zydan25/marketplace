import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ActivityIndicator, FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { router } from "expo-router";
import { useCallback, useEffect, useState } from "react";

import { AdminLayout, AdminBadge, AdminEmptyState, getStatusVariant, Colors, Font, Radius, Shadow, Spacing } from "@/components/admin";
import { apiCall } from "@/lib/_core/api";

type Thread = { id: number; userId: number; status: string; messages: { id: number; body: string; senderRole: string; createdAt: string }[] };

export default function AdminSupportScreen() {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setThreads((await apiCall<{ conversations: Thread[] }>("/api/admin/support")).conversations);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <AdminLayout title="محادثات العملاء">
      {loading ? (
        <ActivityIndicator color={Colors.primary} style={{ marginTop: 40 }} />
      ) : (
        <FlatList
          data={threads}
          keyExtractor={(item) => String(item.id)}
          onRefresh={load}
          refreshing={loading}
          contentContainerStyle={styles.list}
          renderItem={({ item }) => {
            const last = item.messages.at(-1);
            return (
              <TouchableOpacity
                style={styles.card}
                activeOpacity={0.7}
                onPress={() => router.push(`/admin/support/${item.id}` as never)}
              >
                <View style={styles.cardIcon}>
                  <MaterialIcons name="support-agent" size={20} color={Colors.warning} />
                </View>
                <View style={styles.cardCopy}>
                  <View style={styles.cardHeader}>
                    <Text style={styles.cardName}>العميل #{item.userId}</Text>
                    <AdminBadge label={item.status} variant={getStatusVariant(item.status)} />
                  </View>
                  <Text numberOfLines={1} style={styles.cardLast}>{last?.body || "لم تُرسل رسالة بعد"}</Text>
                </View>
                <MaterialIcons name="chevron-left" size={20} color={Colors.textMuted} />
              </TouchableOpacity>
            );
          }}
          ListEmptyComponent={
            <AdminEmptyState
              icon="support-agent"
              title="لا توجد محادثات دعم"
              description="ستظهر محادثات العملاء هنا."
            />
          }
        />
      )}
    </AdminLayout>
  );
}

const styles = StyleSheet.create({
  list: { padding: Spacing.lg, paddingBottom: Spacing["4xl"] },
  card: {
    flexDirection: "row-reverse",
    alignItems: "center",
    backgroundColor: Colors.surface,
    borderRadius: Radius.md,
    padding: Spacing.md,
    marginBottom: Spacing.sm,
    gap: Spacing.md,
    ...Shadow.soft,
  },
  cardIcon: {
    width: 42,
    height: 42,
    borderRadius: Radius.sm,
    backgroundColor: Colors.warningLight,
    alignItems: "center",
    justifyContent: "center",
  },
  cardCopy: { flex: 1, alignItems: "flex-end" },
  cardHeader: { flexDirection: "row-reverse", alignItems: "center", gap: Spacing.sm },
  cardName: { color: Colors.text, ...Font.cardTitle },
  cardLast: { color: Colors.textSecondary, ...Font.tiny, marginTop: Spacing.xs, textAlign: "right" },
});
